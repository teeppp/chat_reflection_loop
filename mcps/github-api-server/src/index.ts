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

const graphqlWithAuth = graphql.defaults({
  headers: {
    authorization: `token ${GITHUB_TOKEN}`,
  },
});

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
                      fieldValues(first: 8) {
                        nodes {
                          ... on ProjectV2ItemFieldTextValue {
                            text
                            field {
                              ... on ProjectV2FieldCommon {
                                name
                              }
                            }
                          }
                          ... on ProjectV2ItemFieldDateValue {
                            date
                            field {
                              ... on ProjectV2FieldCommon {
                                name
                              }
                            }
                          }
                          ... on ProjectV2ItemFieldSingleSelectValue {
                            name
                            field {
                              ... on ProjectV2FieldCommon {
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
          const { projectId, contentId, title } = args as {
            projectId: string;
            contentId?: string;
            title?: string;
          };

          const mutation = contentId ? `
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

          const result = await graphqlWithAuth<
            { addProjectV2ItemById: { item: { id: string } } } | { addProjectV2DraftIssue: { projectItem: { id: string } } }
          >(mutation, {
            input: contentId ? {
              projectId,
              contentId,
            } : {
              projectId,
              title,
            },
          });

          return {
            content: [{
              type: 'text',
              text: JSON.stringify(
                'addProjectV2ItemById' in result ? result.addProjectV2ItemById.item : result.addProjectV2DraftIssue.projectItem,
                null,
                2
              ),
            }],
          };
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
