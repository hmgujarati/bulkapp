import React from 'react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileText } from 'lucide-react';
import { toast } from 'sonner';

const TemplateSelector = ({
  templates,
  selectedTemplate,
  onSelectTemplate,
  onLoadTemplate
}) => {
  const handleSelect = (templateId) => {
    onSelectTemplate(templateId);
    const template = templates.find(t => t.id === templateId);
    if (template) {
      onLoadTemplate(template);
      toast.success(`Template "${template.name}" loaded`);
    }
  };

  if (!templates || templates.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2" data-testid="template-selector">
      <Label className="flex items-center gap-2">
        <FileText className="h-4 w-4 text-purple-600" />
        Load Saved Template
      </Label>
      <Select value={selectedTemplate} onValueChange={handleSelect}>
        <SelectTrigger data-testid="saved-template-select">
          <SelectValue placeholder="Select a saved template..." />
        </SelectTrigger>
        <SelectContent>
          {templates.map(template => (
            <SelectItem key={template.id} value={template.id}>
              {template.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p className="text-xs text-slate-500">
        Load a previously saved template configuration
      </p>
    </div>
  );
};

export default TemplateSelector;
