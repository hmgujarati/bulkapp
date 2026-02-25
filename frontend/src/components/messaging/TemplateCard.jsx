import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Edit, Trash2, Image, Video, FileText, MapPin } from 'lucide-react';

const getMediaBadge = (template) => {
  if (template.header_image) {
    return (
      <Badge variant="outline" className="text-xs">
        <Image className="h-3 w-3 mr-1" /> Image
      </Badge>
    );
  }
  if (template.header_video) {
    return (
      <Badge variant="outline" className="text-xs">
        <Video className="h-3 w-3 mr-1" /> Video
      </Badge>
    );
  }
  if (template.header_document) {
    return (
      <Badge variant="outline" className="text-xs">
        <FileText className="h-3 w-3 mr-1" /> Document
      </Badge>
    );
  }
  if (template.location_latitude && template.location_longitude) {
    return (
      <Badge variant="outline" className="text-xs">
        <MapPin className="h-3 w-3 mr-1" /> Location
      </Badge>
    );
  }
  return null;
};

const TemplateCard = ({ template, onEdit, onDelete }) => {
  const mediaBadge = getMediaBadge(template);

  return (
    <Card className="hover:shadow-md transition-shadow" data-testid={`template-card-${template.id}`}>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-slate-900">{template.name}</h3>
              {mediaBadge}
            </div>
            <p className="text-sm text-slate-500 mb-2">
              Template: <span className="font-mono text-xs">{template.templateName}</span>
            </p>
            
            {/* Field Preview */}
            <div className="text-xs text-slate-400 space-y-0.5">
              {template.field1 && (
                <p className="truncate">Field 1: {template.field1.substring(0, 50)}...</p>
              )}
              {template.field2 && (
                <p className="truncate">Field 2: {template.field2.substring(0, 50)}...</p>
              )}
            </div>
          </div>
          
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(template)}
              data-testid={`edit-template-${template.id}`}
            >
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-red-500 hover:text-red-700"
              onClick={() => onDelete(template.id)}
              data-testid={`delete-template-${template.id}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default TemplateCard;
