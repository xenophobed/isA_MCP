# User File Management API Guide

## Overview

The User File Management API provides secure file upload, storage, and management capabilities integrated with MinIO (development) and AWS S3 (production). All files are user-scoped with automatic access control and presigned URL generation.

**🔒 Security Features:**
- User-scoped file access
- Presigned URLs with 1-hour expiration
- Automatic file organization by date
- Content type validation
- File size limits

## Authentication

All file management endpoints require Bearer Token authentication:

```bash
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data (for uploads)
```

**Supported Token Types:**
- **Auth0 JWT**: RS256 signature algorithm  
- **Supabase JWT**: HS256 signature algorithm

## File Storage Configuration

### Development Environment (MinIO)
- **Storage Provider**: MinIO
- **Endpoint**: localhost:9000
- **Bucket**: user-files
- **Access**: Presigned URLs

### Production Environment (AWS S3)
- **Storage Provider**: AWS S3
- **Region**: Configurable
- **Bucket**: Configurable
- **Access**: Presigned URLs

### File Organization Structure
```
users/
├── {user_id_sanitized}/
│   └── files/
│       └── {year}/
│           └── {month}/
│               └── {timestamp}_{unique_id}.{extension}
```

Example: `users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt`

## Supported File Types

**Allowed File Types:**
- **Documents**: PDF, TXT
- **Spreadsheets**: CSV, Excel (XLS, XLSX)
- **Images**: JPEG, PNG
- **Maximum Size**: 50MB per file

## API Endpoints

### 1. Upload File

**POST** `/api/v1/users/{user_id}/files/upload`

Uploads a file to user-specific storage with automatic organization.

**Request Example:**
```bash
curl -X POST "http://localhost:8100/api/v1/users/auth0%7Ctest456/files/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/your/file.txt"
```

**Success Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "File uploaded successfully",
  "timestamp": "2025-09-06T12:58:53.944969",
  "data": {
    "file_id": "7a08afdc-2bfb-456f-9c1c-44c4b7b6744e",
    "file_path": "users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt",
    "download_url": "http://localhost:9000/user-files/users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20250906%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250906T125853Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=7f60cfe8a603bc544ad21fa238cd7945ffaeb6de472671bc0186c224100f5698",
    "file_size": 46,
    "content_type": "text/plain",
    "uploaded_at": "2025-09-06T12:58:53.944953"
  }
}
```

**Response Fields:**
- `file_id`: Unique identifier for the file
- `file_path`: Storage path within the bucket
- `download_url`: Presigned URL for downloading (valid for 1 hour)
- `file_size`: File size in bytes
- `content_type`: MIME type of the uploaded file
- `uploaded_at`: Upload timestamp

### 2. List User Files

**GET** `/api/v1/users/{user_id}/files`

Retrieves a list of user's files with download URLs.

**Request Example:**
```bash
curl "http://localhost:8100/api/v1/users/auth0%7Ctest456/files?limit=10&prefix=" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query Parameters:**
- `limit` (optional): Maximum number of files to return (default: 100)
- `prefix` (optional): Filter files by path prefix

**Success Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Retrieved 4 files",
  "timestamp": "2025-09-06T12:59:06.715615",
  "data": [
    {
      "file_path": "users/auth0_test456/files/2025/07/20250727_084020_e1ec5840.txt",
      "file_size": 196,
      "content_type": "text/plain",
      "last_modified": "2025-07-27T08:40:20.944000+00:00",
      "etag": "efb4e4aeb1cbce45d8234a213e3a7320",
      "download_url": "http://localhost:9000/user-files/users/auth0_test456/files/2025/07/20250727_084020_e1ec5840.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20250906%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250906T125906Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=f7fda682022afd347d5ff251b2a22a3b9c5ca25d841feb7e7076d1e28db1b1a7"
    },
    {
      "file_path": "users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt",
      "file_size": 46,
      "content_type": "text/plain",
      "last_modified": "2025-09-06T12:58:53.941000+00:00",
      "etag": "4fa829da353823c9458431ebf8ac9478",
      "download_url": "http://localhost:9000/user-files/users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20250906%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250906T125906Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=6b7acc6b1d226f61479c646aad70eddd433d6d4ee3c2400efe9522f3ab251c86"
    }
  ]
}
```

### 3. Get File Information

**GET** `/api/v1/users/{user_id}/files/info`

Retrieves detailed information about a specific file.

**Request Example:**
```bash
curl "http://localhost:8100/api/v1/users/auth0%7Ctest456/files/info?file_path=users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query Parameters:**
- `file_path` (required): Full path to the file in storage

### 4. Delete File

**DELETE** `/api/v1/users/{user_id}/files`

Deletes a specific file from user storage.

**Request Example:**
```bash
curl -X DELETE "http://localhost:8100/api/v1/users/auth0%7Ctest456/files?file_path=users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query Parameters:**
- `file_path` (required): Full path to the file to delete

### 5. Download File

**GET** `/api/v1/users/{user_id}/files/download`

Generates a fresh download URL or redirects to the file.

**Request Example:**
```bash
curl "http://localhost:8100/api/v1/users/auth0%7Ctest456/files/download?file_path=users/auth0_test456/files/2025/09/20250906_125853_bb917cba.txt" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query Parameters:**
- `file_path` (required): Full path to the file to download

## Integration Examples

### JavaScript File Upload

```javascript
class FileManagerClient {
  constructor(baseUrl, authToken) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${authToken}`
    };
  }

  async uploadFile(userId, file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseUrl}/api/v1/users/${encodeURIComponent(userId)}/files/upload`, {
      method: 'POST',
      headers: {
        'Authorization': this.headers.Authorization
        // Don't set Content-Type - let browser handle multipart/form-data
      },
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  async listFiles(userId, options = {}) {
    const params = new URLSearchParams({
      limit: options.limit || 100,
      prefix: options.prefix || ''
    });
    
    const response = await fetch(`${this.baseUrl}/api/v1/users/${encodeURIComponent(userId)}/files?${params}`, {
      headers: this.headers
    });
    
    return response.json();
  }

  async deleteFile(userId, filePath) {
    const params = new URLSearchParams({ file_path: filePath });
    
    const response = await fetch(`${this.baseUrl}/api/v1/users/${encodeURIComponent(userId)}/files?${params}`, {
      method: 'DELETE',
      headers: this.headers
    });
    
    return response.json();
  }
}
```

### React File Upload Component

```javascript
import React, { useState, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

export function FileUpload({ onUploadSuccess }) {
  const { getAccessTokenSilently, user } = useAuth0();
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState([]);

  const handleFileUpload = useCallback(async (selectedFiles) => {
    if (!user?.sub || selectedFiles.length === 0) return;
    
    setUploading(true);
    const token = await getAccessTokenSilently();
    const fileManager = new FileManagerClient('http://localhost:8100', token);
    
    try {
      const uploadPromises = Array.from(selectedFiles).map(file => 
        fileManager.uploadFile(user.sub, file)
      );
      
      const results = await Promise.all(uploadPromises);
      setFiles(prevFiles => [...prevFiles, ...results]);
      onUploadSuccess?.(results);
      
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  }, [user, getAccessTokenSilently, onUploadSuccess]);

  const handleDelete = useCallback(async (filePath) => {
    if (!user?.sub) return;
    
    const token = await getAccessTokenSilently();
    const fileManager = new FileManagerClient('http://localhost:8100', token);
    
    try {
      await fileManager.deleteFile(user.sub, filePath);
      setFiles(files => files.filter(f => f.data.file_path !== filePath));
    } catch (error) {
      console.error('Delete failed:', error);
    }
  }, [user, getAccessTokenSilently]);

  return (
    <div>
      <input 
        type="file" 
        multiple 
        onChange={(e) => handleFileUpload(e.target.files)}
        disabled={uploading}
        accept=".pdf,.csv,.txt,.xlsx,.xls,.jpg,.jpeg,.png"
      />
      
      {uploading && <p>Uploading...</p>}
      
      <div>
        {files.map(file => (
          <div key={file.data.file_id} className="file-item">
            <span>{file.data.file_path}</span>
            <a href={file.data.download_url} target="_blank" rel="noopener noreferrer">
              Download
            </a>
            <button onClick={() => handleDelete(file.data.file_path)}>
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Python File Upload

```python
import requests
import os

class FileManagerClient:
    def __init__(self, base_url, auth_token):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {auth_token}'}
    
    def upload_file(self, user_id, file_path):
        url = f"{self.base_url}/api/v1/users/{user_id}/files/upload"
        
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            response = requests.post(url, headers=self.headers, files=files)
            
        response.raise_for_status()
        return response.json()
    
    def list_files(self, user_id, limit=100, prefix=''):
        url = f"{self.base_url}/api/v1/users/{user_id}/files"
        params = {'limit': limit, 'prefix': prefix}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def delete_file(self, user_id, file_path):
        url = f"{self.base_url}/api/v1/users/{user_id}/files"
        params = {'file_path': file_path}
        
        response = requests.delete(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

# Usage example
client = FileManagerClient('http://localhost:8100', 'your_jwt_token')

# Upload file
result = client.upload_file('auth0|user123', '/path/to/document.pdf')
print(f"File uploaded: {result['data']['file_id']}")

# List files
files = client.list_files('auth0|user123')
print(f"Found {len(files['data'])} files")

# Delete file
client.delete_file('auth0|user123', result['data']['file_path'])
print("File deleted")
```

## Best Practices

### 1. File Validation
Always validate files on the client side before uploading:

```javascript
function validateFile(file) {
  const maxSize = 50 * 1024 * 1024; // 50MB
  const allowedTypes = [
    'application/pdf',
    'text/csv',
    'text/plain',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png'
  ];
  
  if (file.size > maxSize) {
    throw new Error('File size exceeds 50MB limit');
  }
  
  if (!allowedTypes.includes(file.type)) {
    throw new Error('File type not supported');
  }
  
  return true;
}
```

### 2. Progress Tracking
Implement upload progress tracking for better UX:

```javascript
async function uploadWithProgress(userId, file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    };
    
    xhr.onload = () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`));
      }
    };
    
    xhr.open('POST', `/api/v1/users/${encodeURIComponent(userId)}/files/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  });
}
```

### 3. URL Expiration Handling
Presigned URLs expire after 1 hour. Refresh them as needed:

```javascript
class FileWithAutoRefresh {
  constructor(fileInfo, authToken, userId) {
    this.fileInfo = fileInfo;
    this.authToken = authToken;
    this.userId = userId;
    this.urlExpiry = new Date(Date.now() + 60 * 60 * 1000); // 1 hour from now
  }
  
  async getDownloadUrl() {
    if (Date.now() > this.urlExpiry.getTime()) {
      // URL expired, refresh it
      await this.refreshUrl();
    }
    return this.fileInfo.download_url;
  }
  
  async refreshUrl() {
    const response = await fetch(`/api/v1/users/${this.userId}/files/download?file_path=${this.fileInfo.file_path}`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` }
    });
    
    const result = await response.json();
    this.fileInfo.download_url = result.download_url;
    this.urlExpiry = new Date(Date.now() + 60 * 60 * 1000);
  }
}
```

### 4. Error Handling
Implement comprehensive error handling:

```javascript
async function safeFileOperation(operation) {
  try {
    return await operation();
  } catch (error) {
    if (error.response?.status === 413) {
      throw new Error('File too large (50MB limit)');
    } else if (error.response?.status === 415) {
      throw new Error('Unsupported file type');
    } else if (error.response?.status === 403) {
      throw new Error('Access denied - check permissions');
    } else if (error.response?.status === 404) {
      throw new Error('File not found');
    } else {
      throw new Error(`Operation failed: ${error.message}`);
    }
  }
}
```

## Security Considerations

### 1. File Access Control
- Files are automatically scoped to the authenticated user
- Presigned URLs provide secure, time-limited access
- No direct file system access is exposed

### 2. Content Validation
- File types are validated server-side
- File size limits are enforced
- Content scanning may be implemented for security

### 3. URL Security
- Presigned URLs expire after 1 hour
- URLs are generated with proper AWS signatures
- No permanent public access to files

## Error Handling

### Common Error Responses

```json
// File too large
{
  "detail": "File size exceeds maximum allowed size of 50MB"
}

// Unsupported file type
{
  "detail": "File type not supported. Allowed types: PDF, CSV, TXT, XLSX, XLS, JPEG, PNG"
}

// File not found
{
  "success": false,
  "message": "File not found"
}

// Storage error
{
  "detail": "Failed to upload file to storage"
}
```

### HTTP Status Codes
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request (file validation failed)
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: File not found
- `413 Payload Too Large`: File size exceeds limit
- `415 Unsupported Media Type`: File type not allowed
- `500 Internal Server Error`: Storage error

## Related APIs

- [User Management API](how_to_user_api.md) - For user operations
- [Session Management API](how_to_user_api.md#-会话管理-api) - For file-session associations
- [Usage Tracking API](how_to_user_usage.md) - For file processing usage

---

**📝 Last Updated**: 2025-09-06 | API Version: v1.0 | Status: ✅ Tested and Verified