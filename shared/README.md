# Shared Types and Configuration

This directory contains shared TypeScript types and configuration that are used across the frontend and should align with the backend schemas.

## Structure

```
shared/
├── types/
│   ├── recipe.ts      # Recipe domain types (matches backend Pydantic schemas)
│   └── index.ts       # Type exports
└── config/
    ├── constants.ts   # Shared constants (API URLs, etc.)
    └── index.ts       # Config exports
```

## Usage

### In Frontend Components

```typescript
import { Recipe, RecipeLLMOutput, Ingredient, Step } from "../../../shared/types";
import { API_BASE_URL } from "../../../shared/config";
```

## Type Alignment

The TypeScript types in `shared/types/recipe.ts` are designed to match the Pydantic schemas in `server/app/schemas.py`. When updating backend schemas, ensure the corresponding TypeScript types are updated to maintain type safety across the stack.

## Best Practices

1. **Single Source of Truth**: Types are defined once in `shared/types/` and imported where needed
2. **Type Safety**: All API responses should be typed using these shared types
3. **Consistency**: Keep TypeScript types in sync with backend Pydantic schemas
4. **Documentation**: Add JSDoc comments to complex types

