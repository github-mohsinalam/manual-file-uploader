/**
 * Barrel export for all TypeScript types.
 *
 * This file mirrors backend/app/schemas/__init__.py — every type
 * exported from each resource module is re-exported here, so
 * consumers can write:
 *
 *     import type { Template, Domain } from '@/types'
 *
 * instead of importing from each file individually.
 */

export type { Domain } from './domain'

export type {
  Template,
  TemplateCreate,
  TemplateUpdate,
  TemplateStatus,
  FileFormat,
  WriteMode,
  BadRowAction,
} from './template'

export type {
  TemplateColumn,
  TemplateColumnCreate,
  ColumnDataType,
} from './template_column'

export type {
  TemplateReviewer,
  TemplateReviewerCreate,
  ReviewerType,
} from './template_reviewer'

export type {
  TemplateApproval,
  ApprovalAction,
} from './template_approval'

export type {
  ApprovalActionRequest,
  ApprovalActionResponse,
  ApprovalActionVerb,
} from './approval_action'

export type {
  UploadSummary,
  UploadHistory,
  UploadStatus,
} from './upload_history'

export type {
  UploadValidationError,
  ValidationErrorType,
} from './upload_validation_error'