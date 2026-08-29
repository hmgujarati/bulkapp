import { useState } from 'react';
import { toast } from 'sonner';
import api from '../utils/api';

const SIZE_LIMITS = {
  image: 5,
  video: 16,
  document: 10
};

export const useMediaUpload = () => {
  const [uploading, setUploading] = useState(false);

  const uploadFile = async (file, type) => {
    if (!file) return null;

    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    const maxSize = SIZE_LIMITS[type];

    if (fileSizeMB > maxSize) {
      toast.error(`File size (${fileSizeMB.toFixed(2)}MB) exceeds limit (${maxSize}MB)`);
      return null;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('media_type', type);

      const response = await api.post('/upload/media', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        params: { media_type: type }
      });

      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const fullUrl = backendUrl + response.data.url;

      toast.success(`${type.charAt(0).toUpperCase() + type.slice(1)} uploaded successfully`);
      return { url: fullUrl, fileName: file.name };
    } catch (error) {
      toast.error(`Failed to upload ${type}: ${error.response?.data?.detail || error.message}`);
      return null;
    } finally {
      setUploading(false);
    }
  };

  return { uploadFile, uploading };
};

export default useMediaUpload;
