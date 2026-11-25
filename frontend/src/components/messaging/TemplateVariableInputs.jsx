import React from 'react';
import { Plus, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { sanitizeTemplateField, MAX_TEMPLATE_FIELDS, MIN_TEMPLATE_FIELDS } from '../../utils/templateText';

// Variable boxes Field 1..count; optional Add / remove-last controls (max 15)
const TemplateVariableInputs = ({ fields, count, onChange, onAdd, onRemoveLast, testIdPrefix = 'field' }) => (
  <div className="space-y-3">
    {Array.from({ length: count }, (_, i) => i + 1).map(i => (
      <div key={i} className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor={`${testIdPrefix}${i}`}>Field {i}</Label>
          {onRemoveLast && i === count && count > MIN_TEMPLATE_FIELDS && (
            <button
              type="button"
              className="text-xs text-slate-500 hover:text-red-600 flex items-center gap-1"
              onClick={onRemoveLast}
              data-testid={`${testIdPrefix}-remove-last-btn`}
            >
              <X className="h-3 w-3" /> Remove
            </button>
          )}
        </div>
        <Input
          id={`${testIdPrefix}${i}`}
          placeholder={`Value for {{${i}}}`}
          value={fields[`field${i}`] || ''}
          onChange={(e) => onChange(`field${i}`, sanitizeTemplateField(e.target.value))}
          onKeyDown={(e) => { if (e.key === 'Enter') e.preventDefault(); }}
          data-testid={`${testIdPrefix}${i}-input`}
        />
      </div>
    ))}
    {onAdd && count < MAX_TEMPLATE_FIELDS && (
      <Button type="button" variant="outline" size="sm" onClick={onAdd} data-testid={`${testIdPrefix}-add-variable-btn`}>
        <Plus className="h-4 w-4 mr-1" /> Add variable ({count}/{MAX_TEMPLATE_FIELDS})
      </Button>
    )}
  </div>
);

export default TemplateVariableInputs;
