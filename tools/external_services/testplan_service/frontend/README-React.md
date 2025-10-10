# TestPlan Management UI - React + Ant Design

A modern, lightweight, and performance-centric management interface built with React and Ant Design for the TestPlan Management Platform.

## 🚀 Features

### Core Management Sections
- **Dashboard**: Real-time metrics, test execution overview, and system status
- **PICS Management**: Upload, manage, and configure Protocol Implementation Conformance Statements
- **Test Plan Generation**: Generate test plans from 3GPP specification documents
- **Reports & Analytics**: Comprehensive reporting with charts and analytics
- **Settings**: User management, system configuration, and security settings

### Technical Features
- ⚡ **Performance**: Optimized bundle size with tree-shaking and code splitting
- 📱 **Responsive**: Mobile-first design that works on all devices
- 🎨 **Modern UI**: Clean, professional interface using Ant Design components
- 🔒 **Secure**: Role-based access control and security features
- 📊 **Analytics**: Rich charts and visualizations using @ant-design/charts
- 🔄 **Real-time**: Live updates and notifications
- 📤 **File Management**: Drag-and-drop file uploads with progress tracking

## 🛠️ Technology Stack

- **React 18** - Modern React with hooks and concurrent features
- **Ant Design 5** - Enterprise-grade UI component library
- **Vite** - Fast build tool and development server
- **Zustand** - Lightweight state management
- **React Router v6** - Client-side routing
- **@ant-design/charts** - Data visualization components
- **Axios** - HTTP client for API calls
- **TypeScript** - Type safety and better developer experience

## 📦 Installation

1. **Install dependencies**:
   ```bash
   npm install
   # or
   yarn install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

3. **Build for production**:
   ```bash
   npm run build
   # or
   yarn build
   ```

## 🏗️ Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── common/          # Common components (Logo, etc.)
│   └── layout/          # Layout components (MainLayout, etc.)
├── pages/               # Page components
│   ├── Dashboard.jsx    # Dashboard with metrics and charts
│   ├── PicsManagement.jsx # PICS file management
│   ├── TestPlanGeneration.jsx # Test plan creation wizard
│   ├── Reports.jsx      # Reports and analytics
│   └── Settings.jsx     # System and user settings
├── store/               # State management
│   └── appStore.js      # Zustand store
├── styles/              # Global styles
│   └── index.css        # Main stylesheet
└── main.jsx            # Application entry point
```

## 🎯 Key Components

### Dashboard
- Real-time test execution metrics
- Interactive charts showing trends and distributions
- Recent activity timeline
- Quick action buttons

### PICS Management
- Drag-and-drop file upload
- PICS repository with search and filtering
- Version control and status tracking
- Bulk operations support

### Test Plan Generation
- Step-by-step wizard interface
- File upload and parsing
- Test case selection and customization
- Template-based generation

### Reports & Analytics
- Multiple report types (daily, weekly, custom)
- Interactive charts and visualizations
- Export functionality (PDF, Excel)
- Performance analytics

### Settings
- User profile management
- System configuration
- User management (for admins)
- Security settings
- Notification preferences

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=TestPlan Management Platform
VITE_APP_VERSION=1.0.0
```

### API Integration
The application is configured to work with a backend API. Update the `vite.config.js` proxy settings to match your API server:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## 🎨 Customization

### Theme Configuration
Customize the Ant Design theme in `src/main.jsx`:

```javascript
const theme = {
  token: {
    colorPrimary: '#2563EB',
    colorSuccess: '#10B981',
    borderRadius: 8,
    fontFamily: "'Inter', sans-serif",
  },
  components: {
    // Component-specific customizations
  },
}
```

### Adding New Pages
1. Create a new component in `src/pages/`
2. Add the route in `src/App.jsx`
3. Update the navigation menu in `src/components/layout/MainLayout.jsx`

## 📊 Performance Optimizations

- **Bundle Splitting**: Vendor libraries are split into separate chunks
- **Tree Shaking**: Only used components are included in the final bundle
- **Lazy Loading**: Routes and components are loaded on demand
- **Image Optimization**: Images are optimized and served efficiently
- **Caching**: Proper HTTP caching headers for static assets

## 🔒 Security Features

- Role-based access control
- Input validation and sanitization
- CSRF protection
- Secure file uploads
- Session management
- Two-factor authentication support

## 📱 Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Static Hosting
The built files in the `dist/` directory can be served by any static hosting service:
- Nginx
- Apache
- Netlify
- Vercel
- AWS S3 + CloudFront

### Docker Deployment
```dockerfile
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

---

Built with ❤️ using React and Ant Design