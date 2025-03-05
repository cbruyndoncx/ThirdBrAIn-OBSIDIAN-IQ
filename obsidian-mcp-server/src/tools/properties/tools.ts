/**
 * Property-related tool implementations
 */
import { Tool, TextContent } from "@modelcontextprotocol/sdk/types.js";
import { ObsidianClient } from "../../obsidian/client.js";
import { BaseToolHandler } from "../base.js";
import { PropertyManager } from "./manager.js";
import { ObsidianProperties } from "./types.js";
import { createLogger } from "../../utils/logging.js";

// Create a logger for property tools
const logger = createLogger('PropertyTools');

/**
 * Tool names for property operations
 */
export const PROPERTY_TOOL_NAMES = {
  GET_PROPERTIES: "obsidian_get_properties",
  UPDATE_PROPERTIES: "obsidian_update_properties"
} as const;

/**
 * Arguments for getting properties
 */
interface GetPropertiesArgs {
  filepath: string;
}

/**
 * Arguments for updating properties
 */
interface UpdatePropertiesArgs {
  filepath: string;
  properties: Partial<ObsidianProperties>;
  replace?: boolean;
}

/**
 * Tool handler for getting properties from a note
 */
export class GetPropertiesToolHandler extends BaseToolHandler<GetPropertiesArgs> {
  private propertyManager: PropertyManager;

  constructor(client: ObsidianClient) {
    super(PROPERTY_TOOL_NAMES.GET_PROPERTIES, client);
    this.propertyManager = new PropertyManager(client);
  }

  getToolDescription(): Tool {
    return {
      name: this.name,
      description: "Get properties (title, tags, status, etc.) from an Obsidian note's YAML frontmatter. Returns all available properties including custom fields.",
      examples: [
        {
          description: "Get properties from a note",
          args: {
            filepath: "path/to/note.md"
          }
        },
        {
          description: "Get properties from a documentation file",
          args: {
            filepath: "docs/architecture.md"
          }
        }
      ],
      inputSchema: {
        type: "object",
        properties: {
          filepath: {
            type: "string",
            description: "Path to the note file (relative to vault root)",
            format: "path"
          }
        },
        required: ["filepath"]
      }
    };
  }

  async runTool(args: GetPropertiesArgs): Promise<Array<TextContent>> {
    try {
      logger.debug(`Getting properties from: ${args.filepath}`);
      const result = await this.propertyManager.getProperties(args.filepath);
      return this.createResponse(result);
    } catch (error) {
      logger.error(`Error getting properties from ${args.filepath}:`, error);
      return this.handleError(error);
    }
  }
}

/**
 * Tool handler for updating properties in a note
 */
export class UpdatePropertiesToolHandler extends BaseToolHandler<UpdatePropertiesArgs> {
  private propertyManager: PropertyManager;

  constructor(client: ObsidianClient) {
    super(PROPERTY_TOOL_NAMES.UPDATE_PROPERTIES, client);
    this.propertyManager = new PropertyManager(client);
  }

  getToolDescription(): Tool {
    return {
      name: this.name,
      description: "Update properties in an Obsidian note's YAML frontmatter. Intelligently merges arrays (tags, type, status), handles custom fields, and automatically manages timestamps. Valid property types:\n- type: Any string value\n- status: ['draft', 'in-progress', 'review', 'complete']\n- tags: Array of strings starting with '#'\n- Other fields: title, author, version, platform, repository (URI), dependencies, sources, urls (URI), papers, custom (object)",
      examples: [
        {
          description: "Update basic metadata",
          args: {
            filepath: "path/to/note.md",
            properties: {
              title: "Architecture Overview",
              author: "Development Team",
              type: ["architecture", "specification"]
            }
          }
        },
        {
          description: "Update tags and status with replace",
          args: {
            filepath: "docs/feature.md",
            properties: {
              tags: ["#feature", "#in-development", "#high-priority"],
              status: ["in-progress"]
            },
            replace: true
          }
        },
        {
          description: "Add custom fields",
          args: {
            filepath: "projects/project-x.md",
            properties: {
              custom: {
                priority: "high",
                reviewedBy: ["Alice", "Bob"],
                dueDate: "2025-03-01"
              }
            }
          }
        }
      ],
      inputSchema: {
        type: "object",
        properties: {
          filepath: {
            type: "string",
            description: "Path to the note file (relative to vault root)",
            format: "path"
          },
          properties: {
            type: "object",
            description: "Properties to update",
            properties: {
              title: { type: "string" },
              author: { type: "string" },
              type: {
                type: "array",
                items: { type: "string" }
              },
              tags: {
                type: "array",
                items: { type: "string", pattern: "^#" }
              },
              status: {
                type: "array",
                items: {
                  type: "string",
                  enum: ["draft", "in-progress", "review", "complete"]
                }
              },
              version: { type: "string" },
              platform: { type: "string" },
              repository: { type: "string", format: "uri" },
              dependencies: {
                type: "array",
                items: { type: "string" }
              },
              sources: {
                type: "array",
                items: { type: "string" }
              },
              urls: {
                type: "array",
                items: { type: "string", format: "uri" }
              },
              papers: {
                type: "array",
                items: { type: "string" }
              },
              custom: {
                type: "object",
                additionalProperties: true
              }
            },
            additionalProperties: false
          },
          replace: {
            type: "boolean",
            description: "If true, arrays will be replaced instead of merged"
          }
        },
        required: ["filepath", "properties"]
      }
    };
  }

  async runTool(args: UpdatePropertiesArgs): Promise<Array<TextContent>> {
    try {
      logger.debug(`Updating properties for: ${args.filepath}`);
      const result = await this.propertyManager.updateProperties(
        args.filepath,
        args.properties,
        args.replace
      );
      return this.createResponse(result);
    } catch (error) {
      logger.error(`Error updating properties for ${args.filepath}:`, error);
      return this.handleError(error);
    }
  }
}