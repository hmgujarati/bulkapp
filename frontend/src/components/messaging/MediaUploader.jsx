import React from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Upload, Globe, Loader2 } from 'lucide-react';
import useMediaUpload from '../../hooks/useMediaUpload';

const MEDIA_TYPES = [
  { value: 'none', label: 'No Media' },
  { value: 'image', label: 'Image (Header)' },
  { value: 'video', label: 'Video (Header)' },
  { value: 'document', label: 'Document' },
  { value: 'location', label: 'Location' }
];

const MediaUploader = ({
  mediaType,
  onMediaTypeChange,
  headerImage,
  onHeaderImageChange,
  headerVideo,
  onHeaderVideoChange,
  headerDocument,
  onHeaderDocumentChange,
  headerDocumentName,
  onHeaderDocumentNameChange,
  locationLatitude,
  onLocationLatitudeChange,
  locationLongitude,
  onLocationLongitudeChange,
  locationName,
  onLocationNameChange,
  locationAddress,
  onLocationAddressChange,
  className = ''
}) => {
  const { uploadFile, uploading } = useMediaUpload();

  const handleFileChange = async (e, type) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const result = await uploadFile(file, type);
    if (result) {
      if (type === 'image') {
        onHeaderImageChange(result.url);
      } else if (type === 'video') {
        onHeaderVideoChange(result.url);
      } else if (type === 'document') {
        onHeaderDocumentChange(result.url);
        onHeaderDocumentNameChange?.(result.fileName);
      }
    }
  };

  return (
    <div className={`space-y-4 ${className}`} data-testid="media-uploader">
      {/* Media Type Selector */}
      <div className="space-y-2">
        <Label>Media Type</Label>
        <Select value={mediaType} onValueChange={onMediaTypeChange}>
          <SelectTrigger data-testid="media-type-select">
            <SelectValue placeholder="Select media type" />
          </SelectTrigger>
          <SelectContent>
            {MEDIA_TYPES.map(type => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Image Upload */}
      {mediaType === 'image' && (
        <div className="space-y-2">
          <Label>Header Image (Max 5MB)</Label>
          <div className="flex gap-2">
            <Input
              type="file"
              accept="image/*"
              onChange={(e) => handleFileChange(e, 'image')}
              disabled={uploading}
              className="flex-1"
              data-testid="image-upload-input"
            />
            {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
          </div>
          {headerImage && (
            <div className="text-sm text-green-600 flex items-center gap-1">
              <Upload className="h-3 w-3" />
              Image uploaded
            </div>
          )}
          <Input
            placeholder="Or paste image URL"
            value={headerImage}
            onChange={(e) => onHeaderImageChange(e.target.value)}
            data-testid="image-url-input"
          />
        </div>
      )}

      {/* Video Upload */}
      {mediaType === 'video' && (
        <div className="space-y-2">
          <Label>Header Video (Max 16MB)</Label>
          <div className="flex gap-2">
            <Input
              type="file"
              accept="video/*"
              onChange={(e) => handleFileChange(e, 'video')}
              disabled={uploading}
              className="flex-1"
              data-testid="video-upload-input"
            />
            {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
          </div>
          {headerVideo && (
            <div className="text-sm text-green-600 flex items-center gap-1">
              <Upload className="h-3 w-3" />
              Video uploaded
            </div>
          )}
          <Input
            placeholder="Or paste video URL"
            value={headerVideo}
            onChange={(e) => onHeaderVideoChange(e.target.value)}
            data-testid="video-url-input"
          />
        </div>
      )}

      {/* Document Upload */}
      {mediaType === 'document' && (
        <div className="space-y-2">
          <Label>Document (Max 10MB)</Label>
          <div className="flex gap-2">
            <Input
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
              onChange={(e) => handleFileChange(e, 'document')}
              disabled={uploading}
              className="flex-1"
              data-testid="document-upload-input"
            />
            {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
          </div>
          {headerDocument && (
            <div className="text-sm text-green-600 flex items-center gap-1">
              <Upload className="h-3 w-3" />
              {headerDocumentName || 'Document uploaded'}
            </div>
          )}
          <Input
            placeholder="Or paste document URL"
            value={headerDocument}
            onChange={(e) => onHeaderDocumentChange(e.target.value)}
            data-testid="document-url-input"
          />
          <Input
            placeholder="Document filename (e.g., report.pdf)"
            value={headerDocumentName}
            onChange={(e) => onHeaderDocumentNameChange?.(e.target.value)}
            data-testid="document-name-input"
          />
        </div>
      )}

      {/* Location Input */}
      {mediaType === 'location' && (
        <div className="space-y-3 p-4 border rounded-lg bg-slate-50">
          <div className="flex items-center gap-2 text-slate-700">
            <Globe className="h-4 w-4" />
            <span className="font-medium">Location Details</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Latitude *</Label>
              <Input
                type="number"
                step="any"
                placeholder="e.g., 28.7041"
                value={locationLatitude}
                onChange={(e) => onLocationLatitudeChange(e.target.value)}
                required={mediaType === 'location'}
                data-testid="location-latitude-input"
              />
            </div>
            <div>
              <Label>Longitude *</Label>
              <Input
                type="number"
                step="any"
                placeholder="e.g., 77.1025"
                value={locationLongitude}
                onChange={(e) => onLocationLongitudeChange(e.target.value)}
                required={mediaType === 'location'}
                data-testid="location-longitude-input"
              />
            </div>
          </div>
          <div>
            <Label>Location Name</Label>
            <Input
              placeholder="e.g., New Delhi Office"
              value={locationName}
              onChange={(e) => onLocationNameChange(e.target.value)}
              data-testid="location-name-input"
            />
          </div>
          <div>
            <Label>Address</Label>
            <Input
              placeholder="Full address"
              value={locationAddress}
              onChange={(e) => onLocationAddressChange(e.target.value)}
              data-testid="location-address-input"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaUploader;
