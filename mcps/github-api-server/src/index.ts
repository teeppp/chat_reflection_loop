#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { graphql } from '@octokit/graphql';
import * as fs from 'fs';
import * as path from 'path';

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
if (!GITHUB_TOKEN) {
  throw new Error('GITHUB_TOKEN environment variable is required');
}

const graphqlWithAuth = graphql.defaults({
  headers: {
    authorization: `token ${GITHUB_TOKEN}`,
  },
});

// ログファイルの設定
const logDir = path.join(process.cwd(), 'logs');
const logFile = path.join(logDir, 'mcp-server.log');

// ログディレクトリが存在しない場合は作成
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// ログ出力関数
function logToFile(message: string) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  fs.appendFileSync(logFile, logMessage);
}

/**
 * プロジェクトフィールドを管理するクラス
 * フィールドの取得と値の設定を担当
 */
class ProjectFieldManager {
  private fields: Map<string, ProjectV2Field | ProjectV2SingleSelectField>;

  constructor(fields: Array<ProjectV2Field | ProjectV2SingleSelectField>) {
    this.fields = new Map(fields.map(field => [field.name, field]));
  }

  /**
   * 名前でフィールドを取得
   * @param name フィールド名
   * @returns フィールド情報
   */
  getField(name: string): ProjectV2Field | ProjectV2SingleSelectField | undefined {
    return this.fields.get(name);
  }

  /**
   * 単一選択フィールドのオプションを取得
   * @param fieldName フィールド名
   * @param optionName オプション名
   * @returns オプション情報
   * @throws {McpError} フィールドが見つからないか、単一選択フィールドでない場合
   */
  getSingleSelectOption(fieldName: string, optionName: string): { id: string } | undefined {
    const field = this.fields.get(fieldName);
    if (!field) {
      throw new McpError(ErrorCode.InvalidParams, `Field not found: ${fieldName}`);
    }
    if (!('options' in field)) {
      throw new McpError(ErrorCode.InvalidParams, `Field ${fieldName} is not a single select field`);
    }
    return field.options.find(option => option.name === optionName);
  }

  /**
   * プロジェクトフィールドマネージャーを初期化
   * @param projectId プロジェクトID
   * @returns 初期化されたマネージャーインスタンス
   * @throws {McpError} プロジェクトが見つからないか、フィールドの取得に失敗した場合
   */
  static async initialize(projectId: string): Promise<ProjectFieldManager> {
    const query = `
      query($projectId: ID!) {
        node(id: $projectId) {
          ... on ProjectV2 {
            fields(first: 20) {
              nodes {
                ... on ProjectV2Field {
                  id
                  name
                  dataType
                }
                ... on ProjectV2SingleSelectField {
                  id
                  name
                  options {
                    id
                    name
                  }
                }
              }
            }
          }
        }
      }
    `;

    try {
      const result = await graphqlWithAuth<{ node: { fields: { nodes: Array<ProjectV2Field | ProjectV2SingleSelectField> } } }>(query, {
        projectId,
      });

      if (!result.node?.fields?.nodes) {
        throw new McpError(ErrorCode.InvalidParams, `Project not found: ${projectId}`);
      }

      return new ProjectFieldManager(result.node.fields.nodes);
    } catch (error) {
      if (error instanceof McpError) {
        throw error;
      }
      throw new McpError(ErrorCode.InternalError, `Failed to initialize project fields: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}

/**
 * プロジェクトアイテムのフィールド値を設定
 * @param projectId プロジェクトID
 * @param itemId アイテムID
 * @param fieldValue フィールド値の設定内容
 * @throws {McpError} フィールド値の設定に失敗した場合
 */
async function updateProjectItemField(projectId: string, itemId: string, fieldValue: ProjectV2FieldValue): Promise<void> {
  const updateMutation = `
    mutation($input: UpdateProjectV2ItemFieldValueInput!) {
      updateProjectV2ItemFieldValue(input: $input) {
        projectV2Item {
          id
          fieldValues(first: 1) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field { name }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { name }
              }
            }
          }
        }
      }
    }
  `;

  try {
    logToFile(`Updating field value for item ${itemId} in project ${projectId}`);

    // 入力値の検証
    if (!fieldValue.fieldId) {
      throw new McpError(ErrorCode.InvalidParams, 'Field ID is required');
    }

    if (!fieldValue.value.text && !fieldValue.value.singleSelectOptionId) {
      throw new McpError(ErrorCode.InvalidParams, 'Either text or singleSelectOptionId must be provided');
    }

    const result = await graphqlWithAuth<{
      updateProjectV2ItemFieldValue: {
        projectV2Item: {
          id: string;
          fieldValues: {
            nodes: Array<{
              text?: string;
              name?: string;
              field: { name: string };
            }>;
          };
        };
      };
    }>(updateMutation, {
      input: {
        projectId,
        itemId,
        fieldId: fieldValue.fieldId,
        value: fieldValue.value
      },
    });

    if (!result.updateProjectV2ItemFieldValue?.projectV2Item?.id) {
      throw new McpError(ErrorCode.InternalError, 'Failed to update project item field');
    }

    const updatedField = result.updateProjectV2ItemFieldValue.projectV2Item.fieldValues.nodes[0];
    logToFile(`Successfully updated field ${updatedField?.field.name} for item ${itemId}`);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    logToFile(`Error updating field value: ${errorMessage}`);
    if (error instanceof McpError) {
      throw error;
    }
    throw new McpError(ErrorCode.InternalError, `Failed to update field value: ${errorMessage}`);
  }
}

interface CallToolRequest {
  params: {
    name: string;
    arguments?: Record<string, unknown>;
  };
  method: 'tools/call';
}

// GraphQLのレスポンス型定義
interface GetUserIdResponse {
  user: {
    id: string;
  };
}

interface CreateProjectResponse {
  createProjectV2: {
    projectV2: {
      id: string;
      number: number;
      title: string;
      url: string;
    };
  };
}

interface GetProjectResponse {
  user: {
    projectV2: {
      id: string;
      title: string;
      url: string;
      fields: {
        nodes: Array<{
          id: string;
          name: string;
          dataType?: string;
          options?: Array<{
            id: string;
            name: string;
          }>;
        }>;
      };
    };
  };
}

interface ProjectV2FieldBase {
  id: string;
  name: string;
}

interface ProjectV2Field extends ProjectV2FieldBase {
  dataType: string;
}

interface ProjectV2SingleSelectField extends ProjectV2FieldBase {
  options: Array<{
    id: string;
    name: string;
  }>;
}

// フィールド値の型定義
interface ProjectV2FieldValue {
  fieldId: string;
  value: {
    text?: string;
    singleSelectOptionId?: string;
  };
}

interface UpdateProjectV2FieldResponse {
  updateProjectV2Field: {
    projectV2Field: {
      id: string;
      name: string;
      dataType?: string;
      options?: Array<{
        id: string;
        name: string;
      }>;
    };
  };
}

interface CreateProjectFieldResponse {
  createProjectV2Field: {
    projectV2Field: ProjectV2Field | ProjectV2SingleSelectField;
  };
}

interface CreateIssueResponse {
  createIssue: {
    issue: {
      id: string;
      number: number;
      title: string;
      url: string;
    };
  };
}

interface UpdateIssueResponse {
  updateIssue: {
    issue: {
      id: string;
      number: number;
      title: string;
      state: string;
      url: string;
    };
  };
}

interface GetIssueResponse {
  repository: {
    issue: {
      id: string;
      number: number;
      title: string;
      body: string;
      state: string;
      url: string;
      labels: {
        nodes: Array<{
          name: string;
        }>;
      };
    };
  };
}

interface ListProjectItemsResponse {
  node: {
    items: {
      nodes: Array<{
        id: string;
        content: {
          __typename: string;
          title?: string;
          body?: string;
          assignees?: {
            nodes: Array<{
              login: string;
            }>;
          };
        };
        fieldValues: {
          nodes: Array<
            | {
                __typename: 'ProjectV2ItemFieldTextValue';
                text: string;
                field: {
                  name: string;
                };
              }
            | {
                __typename: 'ProjectV2ItemFieldDateValue';
                date: string;
                field: {
                  name: string;
                };
              }
            | {
                __typename: 'ProjectV2ItemFieldSingleSelectValue';
                name: string;
                field: {
                  name: string;
                };
              }
          >;
        };
      }>;
    };
  };
}

async function main() {
  logToFile('Starting GitHub API MCP server...');
  
  const server = new Server(
    {
      name: 'github-api-server',
      version: '0.1.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // エラーログの設定
  server.onerror = (error: Error) => {
    logToFile(`[MCP Error] ${error.message}`);
    console.error('[MCP Error]', error);
  };

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    logToFile('Listing available tools');
    return {
      tools: [
        {
          name: 'create_project',
          description: 'Create a new GitHub Project',
          inputSchema: {
            type: 'object',
            properties: {
              owner: {
                type: 'string',
                description: 'Organization or user name',
              },
              title: {
                type: 'string',
                description: 'Project title',
              },
            },
            required: ['owner', 'title'],
          },
        },
        {
          name: 'get_project',
          description: 'Get GitHub Project information',
          inputSchema: {
            type: 'object',
            properties: {
              owner: {
                type: 'string',
                description: 'Organization or user name',
              },
              number: {
                type: 'number',
                description: 'Project number',
              },
            },
            required: ['owner', 'number'],
          },
        },
        {
          name: 'create_project_field',
          description: 'Create a custom field in a GitHub Project',
          inputSchema: {
            type: 'object',
            properties: {
              projectId: {
                type: 'string',
                description: 'Project node ID',
              },
              name: {
                type: 'string',
                description: 'Field name',
              },
              dataType: {
                type: 'string',
                description: 'Field data type (TEXT, NUMBER, DATE, SINGLE_SELECT, etc.)',
                enum: ['TEXT', 'NUMBER', 'DATE', 'SINGLE_SELECT'],
              },
              options: {
                type: 'array',
                description: 'Options for SINGLE_SELECT fields',
                items: {
                  type: 'object',
                  properties: {
                    name: {
                      type: 'string',
                      description: 'Option name',
                    },
                    color: {
                      type: 'string',
                      description: 'Option color (e.g., BLUE, GREEN, RED)',
                    },
                    description: {
                      type: 'string',
                      description: 'Option description',
                    },
                  },
                  required: ['name', 'color', 'description'],
                },
              },
            },
            required: ['projectId', 'name', 'dataType'],
          },
        },
        {
          name: 'create_issue',
          description: 'Create a new issue in a repository',
          inputSchema: {
            type: 'object',
            properties: {
              owner: {
                type: 'string',
                description: 'Repository owner',
              },
              repo: {
                type: 'string',
                description: 'Repository name',
              },
              title: {
                type: 'string',
                description: 'Issue title',
              },
              body: {
                type: 'string',
                description: 'Issue body',
              },
              labels: {
                type: 'array',
                description: 'Issue labels',
                items: {
                  type: 'string',
                },
              },
            },
            required: ['owner', 'repo', 'title'],
          },
        },
        {
          name: 'update_issue',
          description: 'Update an existing issue',
          inputSchema: {
            type: 'object',
            properties: {
              owner: {
                type: 'string',
                description: 'Repository owner',
              },
              repo: {
                type: 'string',
                description: 'Repository name',
              },
              number: {
                type: 'number',
                description: 'Issue number',
              },
              title: {
                type: 'string',
                description: 'New issue title',
              },
              body: {
                type: 'string',
                description: 'New issue body',
              },
              state: {
                type: 'string',
                description: 'Issue state (OPEN or CLOSED)',
                enum: ['OPEN', 'CLOSED'],
              },
            },
            required: ['owner', 'repo', 'number'],
          },
        },
        {
          name: 'get_issue',
          description: 'Get issue information',
          inputSchema: {
            type: 'object',
            properties: {
              owner: {
                type: 'string',
                description: 'Repository owner',
              },
              repo: {
                type: 'string',
                description: 'Repository name',
              },
              number: {
                type: 'number',
                description: 'Issue number',
              },
            },
            required: ['owner', 'repo', 'number'],
          },
        },
        {
          name: 'list_project_items',
          description: 'List all items in a project',
          inputSchema: {
            type: 'object',
            properties: {
              projectId: {
                type: 'string',
                description: 'Project node ID',
              },
            },
            required: ['projectId'],
          },
        },
        {
          name: 'create_project_item',
          description: 'Create a new item in a GitHub Project',
          inputSchema: {
            type: 'object',
            properties: {
              projectId: {
                type: 'string',
                description: 'Project node ID',
              },
              contentId: {
                type: 'string',
                description: 'Issue node ID (optional)',
              },
              title: {
                type: 'string',
                description: 'Item title (required if contentId is not provided)',
              },
              body: {
                type: 'string',
                description: 'Item body for Draft Issue',
              },
              bodyField: {
                type: 'string',
                description: 'Set body to Description field',
              },
              type: {
                type: 'string',
                description: 'Item type (PBI, SBI, Task, Bug, Epic)',
                enum: ['PBI', 'SBI', 'Task', 'Bug', 'Epic'],
              },
            },
            required: ['projectId'],
          },
        },
        {
          name: 'convert_project_item_to_issue',
          description: 'Convert a project item to an issue',
          inputSchema: {
            type: 'object',
            properties: {
              projectId: {
                type: 'string',
                description: 'Project node ID',
              },
              itemId: {
                type: 'string',
                description: 'Project item node ID',
              },
              owner: {
                type: 'string',
                description: 'Repository owner',
              },
              repo: {
                type: 'string',
                description: 'Repository name',
              },
            },
            required: ['projectId', 'itemId', 'owner', 'repo'],
          },
        },
        {
          name: 'update_project_v2_field',
          description: 'Update a project field',
          inputSchema: {
            type: 'object',
            properties: {
              fieldId: {
                type: 'string',
                description: 'Field ID to update',
              },
              name: {
                type: 'string',
                description: 'New field name',
              },
              singleSelectOptions: {
                type: 'array',
                description: 'Options for SINGLE_SELECT fields. If provided, will overwrite existing options.',
                items: {
                  type: 'object',
                  properties: {
                    name: {
                      type: 'string',
                      description: 'Option name',
                    },
                    color: {
                      type: 'string',
                      description: 'Option color (e.g., BLUE, GREEN, RED)',
                    },
                    description: {
                      type: 'string',
                      description: 'Option description',
                    },
                  },
                  required: ['name', 'color', 'description'],
                },
              },
            },
            required: ['fieldId'],
          },
        },
      ],
    };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
    logToFile(`Handling tool request: ${request.params.name}`);
    
    const args = request.params.arguments;
    if (!args || typeof args !== 'object') {
      throw new McpError(ErrorCode.InvalidParams, 'Arguments are required');
    }

    try {
      switch (request.params.name) {
        case 'create_project': {
          const { owner, title } = args as { owner: string; title: string };
          
          // まずユーザーのIDを取得
          const userQuery = `
            query($login: String!) {
              user(login: $login) {
                id
              }
            }
          `;

          const userResult = await graphqlWithAuth<GetUserIdResponse>(userQuery, {
            login: owner,
          });

          if (!userResult.user?.id) {
            throw new Error(`User ${owner} not found`);
          }

          const mutation = `
            mutation($input: CreateProjectV2Input!) {
              createProjectV2(input: $input) {
                projectV2 {
                  id
                  number
                  title
                  url
                }
              }
            }
          `;

          const result = await graphqlWithAuth<CreateProjectResponse>(mutation, {
            input: {
              ownerId: userResult.user.id,
              title,
            },
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.createProjectV2.projectV2, null, 2),
            }],
          };
        }

        case 'get_project': {
          const { owner, number } = args as { owner: string; number: number };
          
          const query = `
            query($owner: String!, $number: Int!) {
              user(login: $owner) {
                projectV2(number: $number) {
                  id
                  title
                  url
                  fields(first: 20) {
                    nodes {
                      ... on ProjectV2Field {
                        id
                        name
                        dataType
                      }
                      ... on ProjectV2SingleSelectField {
                        id
                        name
                        options {
                          id
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          `;

          const result = await graphqlWithAuth<GetProjectResponse>(query, {
            owner,
            number,
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.user.projectV2, null, 2),
            }],
          };
        }

        case 'create_project_field': {
          const { projectId, name, dataType, options = [] } = args as {
            projectId: string;
            name: string;
            dataType: string;
            options?: Array<{
              name: string;
              color: string;
              description: string;
            }>;
          };

          const mutation = `
            mutation($input: CreateProjectV2FieldInput!) {
              createProjectV2Field(input: $input) {
                projectV2Field {
                  ... on ProjectV2Field {
                    id
                    name
                    dataType
                  }
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options {
                      id
                      name
                    }
                  }
                }
              }
            }
          `;

          const result = await graphqlWithAuth<CreateProjectFieldResponse>(mutation, {
            input: {
              projectId,
              name,
              dataType,
              ...(dataType === 'SINGLE_SELECT' && {
                singleSelectOptions: options,
              }),
            },
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.createProjectV2Field.projectV2Field, null, 2),
            }],
          };
        }

        case 'create_issue': {
          const { owner, repo, title, body = '', labels = [] } = args as {
            owner: string;
            repo: string;
            title: string;
            body?: string;
            labels?: string[];
          };

          // リポジトリIDを取得
          const repoQuery = `
            query($owner: String!, $repo: String!) {
              repository(owner: $owner, name: $repo) {
                id
              }
            }
          `;

          const repoResult = await graphqlWithAuth<{ repository: { id: string } }>(repoQuery, {
            owner,
            repo,
          });

          logToFile(`Repository ID: ${JSON.stringify(repoResult)}`);

          if (!repoResult.repository?.id) {
            throw new Error(`Repository ${owner}/${repo} not found`);
          }

          const mutation = `
            mutation($input: CreateIssueInput!) {
              createIssue(input: $input) {
                issue {
                  id
                  number
                  title
                  url
                }
              }
            }
          `;

          // ラベルが存在するか確認
          const labelQuery = `
            query($owner: String!, $repo: String!, $name: String!) {
              repository(owner: $owner, name: $repo) {
                label(name: $name) {
                  id
                }
              }
            }
          `;

          const labelResults = await Promise.all(
            labels.map(async (label) => {
              const labelResult = await graphqlWithAuth<{
                repository: { label: { id: string } };
              }>(labelQuery, {
                owner,
                repo,
                name: label,
              });
              return labelResult.repository?.label?.id;
            })
          );

          const labelIds = labelResults.filter(Boolean);

          // ラベルが存在しない場合は作成
          const createLabelMutation = `
            mutation($input: CreateLabelInput!) {
              createLabel(input: $input) {
                label {
                  id
                }
              }
            }
          `;

          const newLabelIds = await Promise.all(
            labels.map(async (label, index) => {
              if (labelIds[index]) {
                return labelIds[index];
              }
              const createLabelResult = await graphqlWithAuth<{
                createLabel: { label: { id: string } };
              }>(createLabelMutation, {
                input: {
                  repositoryId: repoResult.repository.id,
                  name: label,
                  color: 'ededed',
                },
              });
              return createLabelResult.createLabel.label.id;
            })
          );

          const result = await graphqlWithAuth<CreateIssueResponse>(mutation, {
            input: {
              repositoryId: repoResult.repository.id,
              title,
              body,
              labelIds: newLabelIds,
            },
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.createIssue.issue, null, 2),
            }],
          };
        }

        case 'update_issue': {
          const { owner, repo, number, title, body, state } = args as {
            owner: string;
            repo: string;
            number: number;
            title?: string;
            body?: string;
            state?: string;
          };

          const mutation = `
            mutation($input: UpdateIssueInput!) {
              updateIssue(input: $input) {
                issue {
                  id
                  number
                  title
                  state
                  url
                }
              }
            }
          `;

          const result = await graphqlWithAuth<UpdateIssueResponse>(mutation, {
            input: {
              id: `${owner}/${repo}/issues/${number}`,
              ...(title && { title }),
              ...(body && { body }),
              ...(state && { state }),
            },
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.updateIssue.issue, null, 2),
            }],
          };
        }

        case 'get_issue': {
          const { owner, repo, number } = args as {
            owner: string;
            repo: string;
            number: number;
          };

          const query = `
            query($owner: String!, $repo: String!, $number: Int!) {
              repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                  id
                  number
                  title
                  body
                  state
                  url
                  labels(first: 10) {
                    nodes {
                      name
                    }
                  }
                }
              }
            }
          `;

          const result = await graphqlWithAuth<GetIssueResponse>(query, {
            owner,
            repo,
            number,
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.repository.issue, null, 2),
            }],
          };
        }

        case 'list_project_items': {
          const { projectId } = args as { projectId: string };

          const query = `
            query($projectId: ID!) {
              node(id: $projectId) {
                ... on ProjectV2 {
                  items(first: 20) {
                    nodes {
                      id
                      fieldValues(first: 20) {
                        nodes {
                          ... on ProjectV2ItemFieldTextValue {
                            text
                            field {
                              ... on ProjectV2FieldCommon {
                                id
                                name
                              }
                            }
                          }
                          ... on ProjectV2ItemFieldDateValue {
                            date
                            field {
                              ... on ProjectV2FieldCommon {
                                id
                                name
                              }
                            }
                          }
                          ... on ProjectV2ItemFieldSingleSelectValue {
                            name
                            field {
                              ... on ProjectV2FieldCommon {
                                id
                                name
                              }
                            }
                          }
                        }
                      }
                      content {
                        ... on DraftIssue {
                          title
                          body
                        }
                        ... on Issue {
                          title
                          assignees(first: 10) {
                            nodes {
                              login
                            }
                          }
                        }
                        ... on PullRequest {
                          title
                          assignees(first: 10) {
                            nodes {
                              login
                            }
                          }
                        }
                      }
                      content {
                        ... on DraftIssue {
                          title
                          body
                        }
                        ...on Issue {
                          title
                          assignees(first: 10) {
                            nodes {
                              login
                            }
                          }
                        }
                        ...on PullRequest {
                          title
                          assignees(first: 10) {
                            nodes {
                              login
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          `;

          const result = await graphqlWithAuth<ListProjectItemsResponse>(query, {
            projectId,
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.node.items.nodes, null, 2),
            }],
          };
        }
        case 'create_project_item': {
          // 1. パラメータの型定義
          type CreateProjectItemParams = {
            projectId: string;
            contentId?: string;
            title?: string;
            type?: string;
            ready?: string;
            body?: string;
            bodyField?: string;
          };

          try {
            // 2. パラメータのバリデーション
            const params = args as unknown as CreateProjectItemParams;

            if (!params.projectId) {
              throw new McpError(ErrorCode.InvalidParams, 'Project ID is required');
            }

            if (!params.contentId && !params.title) {
              throw new McpError(ErrorCode.InvalidParams, 'Either contentId or title must be provided');
            }

            logToFile(`Creating project item with parameters: ${JSON.stringify(params)}`);

            // 3. プロジェクトアイテムの作成
            const createMutation = params.contentId ? `
              mutation($input: AddProjectV2ItemByIdInput!) {
                addProjectV2ItemById(input: $input) {
                  item {
                    id
                  }
                }
              }
            ` : `
              mutation($input: AddProjectV2DraftIssueInput!) {
                addProjectV2DraftIssue(input: $input) {
                  projectItem {
                    id
                  }
                }
              }
            `;

            type CreateItemResult = {
              addProjectV2ItemById?: { item: { id: string } };
              addProjectV2DraftIssue?: { projectItem: { id: string } };
            };

            const createInput = params.contentId ? {
              projectId: params.projectId,
              contentId: params.contentId,
            } : {
              projectId: params.projectId,
              title: params.title,
              body: params.body
            };

            const createResult = await graphqlWithAuth<CreateItemResult>(createMutation, {
              input: createInput,
            });

            const itemId = createResult.addProjectV2ItemById?.item.id ?? createResult.addProjectV2DraftIssue?.projectItem.id;

            if (!itemId) {
              throw new McpError(ErrorCode.InternalError, 'Failed to create project item');
            }

            logToFile(`Project item created with ID: ${itemId}`);

            // 4. フィールド値の設定
            const fieldManager = await ProjectFieldManager.initialize(params.projectId);
            logToFile('Project fields initialized successfully');

            // フィールド値の設定
            try {
              // Ready フィールドの設定
              if (params.ready) {
                const readyFieldData = fieldManager.getField('Ready?') as ProjectV2SingleSelectField;
                if (!readyFieldData) {
                  throw new McpError(ErrorCode.InvalidParams, 'Ready? field not found in project');
                }
                const readyOption = fieldManager.getSingleSelectOption('Ready?', params.ready);
                if (!readyOption) {
                  throw new McpError(ErrorCode.InvalidParams, `Invalid Ready option: ${params.ready}`);
                }
                await updateProjectItemField(params.projectId, itemId, {
                  fieldId: readyFieldData.id,
                  value: {
                    singleSelectOptionId: readyOption.id
                  }
                });
                logToFile(`Set Ready field to: ${params.ready}`);
              }

              // Type フィールドの設定
              if (params.type) {
                const typeFieldData = fieldManager.getField('Type') as ProjectV2SingleSelectField;
                if (!typeFieldData) {
                  throw new McpError(ErrorCode.InvalidParams, 'Type field not found in project');
                }
                const typeOption = fieldManager.getSingleSelectOption('Type', params.type);
                if (!typeOption) {
                  throw new McpError(ErrorCode.InvalidParams, `Invalid Type option: ${params.type}`);
                }
                await updateProjectItemField(params.projectId, itemId, {
                  fieldId: typeFieldData.id,
                  value: {
                    singleSelectOptionId: typeOption.id
                  }
                });
                logToFile(`Set Type field to: ${params.type}`);
              }

              // Description フィールドの設定
              if (params.body) {
                const descriptionFieldName = params.bodyField || 'Description';
                const descriptionFieldData = fieldManager.getField(descriptionFieldName) as ProjectV2Field;
                if (!descriptionFieldData) {
                  throw new McpError(ErrorCode.InvalidParams, `${descriptionFieldName} field not found in project`);
                }
                await updateProjectItemField(params.projectId, itemId, {
                  fieldId: descriptionFieldData.id,
                  value: {
                    text: params.body
                  }
                });
                logToFile(`Set ${descriptionFieldName} field with body content`);
              }
            } catch (error) {
              // フィールド更新中のエラーをログに記録し、適切なエラーを投げる
              const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
              logToFile(`Error updating fields: ${errorMessage}`);
              if (error instanceof McpError) {
                throw error;
              }
              throw new McpError(ErrorCode.InternalError, `Failed to update fields: ${errorMessage}`);
            }

            return {
              content: [{
                type: 'text',
                text: JSON.stringify({ id: itemId }, null, 2),
              }],
            };

          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
            logToFile(`Error in create_project_item: ${errorMessage}`);
            if (error instanceof McpError) {
              throw error;
            }
            throw new McpError(ErrorCode.InternalError, `Failed to create project item: ${errorMessage}`);
          }
        }
        case 'update_project_v2_field': {
          const { fieldId, name, singleSelectOptions } = args as {
            fieldId: string;
            name?: string;
            singleSelectOptions?: Array<{
              name: string;
              color: string;
              description: string;
            }>;
          };

          // バリデーションチェック
          if (!fieldId) {
            throw new McpError(ErrorCode.InvalidParams, 'Field ID is required');
          }

          logToFile(`Updating project field: ${fieldId}`);

          const mutation = `
            mutation($input: UpdateProjectV2FieldInput!) {
              updateProjectV2Field(input: $input) {
                projectV2Field {
                  ... on ProjectV2Field {
                    id
                    name
                    dataType
                  }
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options {
                      id
                      name
                    }
                  }
                }
              }
            }
          `;

          try {
            const result = await graphqlWithAuth<UpdateProjectV2FieldResponse>(mutation, {
              input: {
                fieldId,
                ...(name && { name }),
                ...(singleSelectOptions && { singleSelectOptions }),
              },
            });

            if (!result.updateProjectV2Field?.projectV2Field) {
              throw new McpError(ErrorCode.InternalError, 'Failed to update project field');
            }

            logToFile(`Successfully updated field ${fieldId}`);

            return {
              content: [{
                type: 'text',
                text: JSON.stringify(result.updateProjectV2Field.projectV2Field, null, 2),
              }],
            };
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
            logToFile(`Error updating project field: ${errorMessage}`);
            if (error instanceof McpError) {
              throw error;
            }
            throw new McpError(ErrorCode.InternalError, `Failed to update project field: ${errorMessage}`);
          }
        }

        case 'convert_project_item_to_issue': {
          const { projectId, itemId, owner, repo } = args as {
            projectId: string;
            itemId: string;
            owner: string;
            repo: string;
          };

          // リポジトリIDを取得
          const repoQuery = `
            query($owner: String!, $name: String!) {
              repository(owner: $owner, name: $name) {
                id
              }
            }
          `;

          const repoResult = await graphqlWithAuth<{ repository: { id: string } }>(repoQuery, {
            owner,
            name: repo,
          });

          if (!repoResult.repository?.id) {
            throw new Error(`Repository ${owner}/${repo} not found`);
          }

          const mutation = `
            mutation($input: ConvertProjectV2DraftIssueItemToIssueInput!) {
              convertProjectV2DraftIssueItemToIssue(input: $input) {
                 item {
                  id
                  content {
                    ... on Issue {
                      __typename
                      id
                      number
                      title
                      url
                    }
                  }
                }
              }
            }
          `;

          const result = await graphqlWithAuth<
            { convertProjectV2DraftIssueItemToIssue: { item: { id: string, content: { __typename: string, id: string, number: number, title: string, url: string } } } }
          >(mutation, {
            input: {
              itemId: itemId,
              repositoryId: repoResult.repository.id,
            },
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result.convertProjectV2DraftIssueItemToIssue.item.content, null, 2),
            }],
          };
        }
        default:
          throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error occurred';
      logToFile(`GitHub API error: ${message}`);
      return {
        content: [{
          type: 'text',
          text: `GitHub API error: ${message}`,
        }],
        isError: true,
      };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  logToFile('GitHub API MCP server running on stdio');
  console.error('GitHub API MCP server running on stdio');
}

main().catch((error) => {
  logToFile(`Fatal error: ${error.message}`);
  console.error('Fatal error:', error);
  process.exit(1);
});
