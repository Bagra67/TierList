import { describe, expect, it } from 'vitest';

import { readRepositoryFile } from '../test/repositoryFile';
import { DISPLAY_NAME_MAX_LENGTH, PASSWORD_MAX_LENGTH } from './auth';
import { MODERATION_REASON_MAX_LENGTH, REPORT_DETAILS_MAX_LENGTH } from './moderation';
import { CONFIRM_PARAM, LOGIN_ERROR_PARAM, ROUTES, TOKEN_PARAM } from './routes';
import {
  TEMPLATE_NAME_MAX_LENGTH,
  TIER_COLOR_PRESETS,
  TIER_NAME_MAX_LENGTH,
  TILE_TEXT_MAX_LENGTH,
} from './templates';

interface OpenApiProperty {
  maxLength?: number;
  pattern?: string;
  anyOf?: OpenApiProperty[];
}

interface OpenApiSchemas {
  components: { schemas: Record<string, { properties: Record<string, OpenApiProperty> }> };
}

const openApiSchemas: OpenApiSchemas['components']['schemas'] = (
  JSON.parse(readRepositoryFile('backend/openapi.json')) as OpenApiSchemas
).components.schemas;
const backendAuthConstants: string = readRepositoryFile('backend/app/constants/auth.py');
const backendRoomConstants: string = readRepositoryFile('backend/app/constants/rooms.py');
const backendTemplateConstants: string = readRepositoryFile('backend/app/constants/templates.py');

function maxLengthOf(schemaName: string, propertyName: string): number | undefined {
  const property: OpenApiProperty = openApiSchemas[schemaName].properties[propertyName];
  const options: OpenApiProperty[] = [property, ...(property.anyOf ?? [])];
  return options.find((option: OpenApiProperty) => option.maxLength !== undefined)?.maxLength;
}

function pythonStringConstant(pythonSource: string, name: string): string {
  const assignment: RegExpMatchArray | null = pythonSource.match(
    new RegExp(`^${name} = "([^"]*)"`, 'm'),
  );
  if (assignment === null) throw new Error(`No constant ${name}`);
  return assignment[1];
}

function backendDefaultTierColors(): string[] {
  const block: RegExpMatchArray | null = backendTemplateConstants.match(
    /^DEFAULT_TIERS[^=]*= \(([\s\S]*?)^\)/m,
  );
  if (block === null) throw new Error('No DEFAULT_TIERS');
  return [...block[1].matchAll(/#[0-9A-Fa-f]{6}/g)].map((color: RegExpExecArray) => color[0]);
}

describe('limits shared with the backend', () => {
  it('caps the password and the display name at the limits of the register request', () => {
    const registerProperties: Record<string, OpenApiProperty> =
      openApiSchemas.RegisterRequest.properties;

    expect(PASSWORD_MAX_LENGTH).toBe(registerProperties.password.maxLength);
    expect(DISPLAY_NAME_MAX_LENGTH).toBe(registerProperties.display_name.maxLength);
  });

  it('caps the moderation reason at the limit of the moderation and ban requests', () => {
    for (const schemaName of ['ModerationReasonRequest', 'BanAccountRequest']) {
      expect(MODERATION_REASON_MAX_LENGTH).toBe(
        openApiSchemas[schemaName].properties.reason.maxLength,
      );
    }
  });
});

describe('report limits shared with the backend', () => {
  it('caps the details at the limit of the report request', () => {
    expect(REPORT_DETAILS_MAX_LENGTH).toBe(maxLengthOf('CreateReportRequest', 'details'));
  });
});

describe('template limits shared with the backend', () => {
  it('caps the names and the tile text at the limits of the template requests', () => {
    for (const schemaName of ['CreateTemplateRequest', 'RenameTemplateRequest']) {
      expect(TEMPLATE_NAME_MAX_LENGTH).toBe(maxLengthOf(schemaName, 'name'));
    }
    expect(TIER_NAME_MAX_LENGTH).toBe(maxLengthOf('UpdateTierRequest', 'name'));
    for (const schemaName of ['CreateTileRequest', 'UpdateTileRequest']) {
      expect(TILE_TEXT_MAX_LENGTH).toBe(maxLengthOf(schemaName, 'text'));
    }
  });
});

describe('addresses shared with the backend', () => {
  it('has a page for each redirection after Google', () => {
    expect(ROUTES.HOME).toBe(pythonStringConstant(backendAuthConstants, 'FRONTEND_HOME'));
    expect(ROUTES.LOGIN).toBe(pythonStringConstant(backendAuthConstants, 'FRONTEND_LOGIN'));
  });

  it('has a page for each link sent by email', () => {
    expect(ROUTES.VERIFY_EMAIL).toBe(
      pythonStringConstant(backendAuthConstants, 'FRONTEND_VERIFY_EMAIL'),
    );
    expect(ROUTES.RESET_PASSWORD).toBe(
      pythonStringConstant(backendAuthConstants, 'FRONTEND_RESET_PASSWORD'),
    );
  });

  it('has a page for the shared link of a room', () => {
    expect(ROUTES.ROOM).toBe(
      `${pythonStringConstant(backendRoomConstants, 'FRONTEND_ROOM')}/:code`,
    );
  });

  it('reads the query parameters under the names the backend writes', () => {
    expect(TOKEN_PARAM).toBe(pythonStringConstant(backendAuthConstants, 'TOKEN_PARAM'));
    expect(LOGIN_ERROR_PARAM).toBe(pythonStringConstant(backendAuthConstants, 'LOGIN_ERROR_PARAM'));
    expect(CONFIRM_PARAM).toBe(pythonStringConstant(backendAuthConstants, 'CONFIRM_PARAM'));
  });
});

describe('tier color presets', () => {
  it('start with the colors of the default tiers and end with the grey of a new tier', () => {
    const defaultTierColors: string[] = backendDefaultTierColors();

    expect(defaultTierColors).toHaveLength(6);
    expect(TIER_COLOR_PRESETS.slice(0, defaultTierColors.length)).toEqual(defaultTierColors);
    expect(TIER_COLOR_PRESETS.at(-1)).toBe(
      pythonStringConstant(backendTemplateConstants, 'NEW_TIER_COLOR'),
    );
  });

  it('are twelve, to fill two rows of six', () => {
    expect(TIER_COLOR_PRESETS).toHaveLength(12);
  });

  it('are only suggestions: the backend accepts any #RRGGBB color', () => {
    const colorOutsideThePresets: string = '#123ABC';
    const acceptedColor: OpenApiProperty | undefined =
      openApiSchemas.UpdateTierRequest.properties.color.anyOf?.find(
        (variant: OpenApiProperty) => variant.pattern !== undefined,
      );

    expect(TIER_COLOR_PRESETS).not.toContain(colorOutsideThePresets);
    expect(colorOutsideThePresets).toMatch(new RegExp(acceptedColor?.pattern ?? '^$'));
  });
});
