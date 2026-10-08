import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';
export const collections = { i18n: defineCollection({loader:i18nLoader(),schema:i18nSchema()}), docs: defineCollection({loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/docs' }),schema:docsSchema({extend:z.object({kind:z.literal('digest').optional(),batch_id:z.string().optional(),model:z.string().optional(),prompt_version:z.string().optional(),schema_version:z.string().optional(),enriched_at:z.string().optional(),reviewed_at:z.string().nullable().optional(),demo:z.boolean().optional()})})}) };
