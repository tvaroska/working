# Updater Frontend

Modern React frontend for Updater - AI-powered content aggregation platform built with Next.js 15, React 19, and Tailwind CSS.

## 🚀 Features

- **Modern Stack**: Next.js 15 with React 19 and TypeScript
- **Beautiful UI**: Tailwind CSS with custom design system
- **Responsive Design**: Mobile-first approach with fluid layouts
- **PWA Ready**: Progressive Web App with offline capabilities
- **Animations**: Smooth animations with Framer Motion
- **Performance**: Optimized for Core Web Vitals
- **Accessibility**: WCAG 2.1 AA compliant

## 🛠️ Technology Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Heroicons & Lucide React
- **Animations**: Framer Motion
- **Components**: Headless UI
- **Build Tool**: Built-in Next.js compiler

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/          # React components
│   │   ├── Header.tsx       # Navigation header
│   │   ├── Hero.tsx         # Hero section
│   │   ├── Features.tsx     # Features showcase
│   │   ├── HowItWorks.tsx   # Process explanation
│   │   ├── Testimonials.tsx # User testimonials
│   │   ├── Pricing.tsx      # Pricing plans
│   │   ├── CTA.tsx          # Call-to-action
│   │   └── Footer.tsx       # Site footer
│   ├── utils/               # Utility functions
│   └── types/               # TypeScript types
├── public/                  # Static assets
│   ├── manifest.json        # PWA manifest
│   ├── sw.js               # Service worker
│   └── icons/              # App icons
├── tailwind.config.js       # Tailwind configuration
├── next.config.js          # Next.js configuration
└── tsconfig.json           # TypeScript configuration
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Modern web browser

### Installation

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript checks
```

## 🎨 Design System

### Colors

- **Primary**: Blue scale (primary-50 to primary-950)
- **Gray**: Neutral scale (gray-50 to gray-950)
- **Success**: Green for positive actions
- **Warning**: Yellow for cautions
- **Error**: Red for errors

### Typography

- **Font Family**: Inter (primary), JetBrains Mono (code)
- **Headings**: Bold weights with proper hierarchy
- **Body**: Regular weight with optimal line height

### Components

- **Buttons**: Primary, secondary, and ghost variants
- **Cards**: Clean design with subtle shadows
- **Forms**: Consistent styling with focus states
- **Navigation**: Mobile-responsive with smooth transitions

## 📱 PWA Features

### Offline Capabilities

- Service worker for offline functionality
- Cache-first strategy for static assets
- Network-first for dynamic content
- Background sync for offline actions

### Installation

- Installable on desktop and mobile
- Custom app icons and splash screens
- Shortcuts for quick access
- Edge sidebar support

### Performance

- Critical resource preloading
- Image optimization
- Code splitting
- Compression and minification

## 🎯 Performance Optimizations

### Core Web Vitals

- **LCP**: Optimized image loading and critical CSS
- **FID**: Minimal JavaScript on initial load
- **CLS**: Stable layouts with proper sizing

### Techniques Used

- Next.js automatic code splitting
- Image optimization with `next/image`
- Font optimization with `next/font`
- Static generation where possible
- Progressive loading for dynamic content

## 🔧 Configuration

### Environment Variables

Create `.env.local` file:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# Optional: Analytics
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
GOOGLE_VERIFICATION=verification_string
```

### Tailwind Customization

The design system is configured in `tailwind.config.js`:

- Custom color palette
- Extended animations
- Custom utilities
- Component classes

### Next.js Configuration

`next.config.js` includes:

- Image domain allowlist
- Experimental optimizations
- PWA headers
- Environment variable exposure

## 📐 Responsive Design

### Breakpoints

- **sm**: 640px+ (Mobile landscape)
- **md**: 768px+ (Tablet)
- **lg**: 1024px+ (Desktop)
- **xl**: 1280px+ (Large desktop)
- **2xl**: 1536px+ (Extra large)

### Mobile-First Approach

- Base styles target mobile
- Progressive enhancement for larger screens
- Touch-friendly interactions
- Optimized content hierarchy

## ♿ Accessibility

### Standards Compliance

- WCAG 2.1 AA guidelines
- Semantic HTML structure
- Proper ARIA labels
- Keyboard navigation support

### Features

- Focus management
- Screen reader support
- High contrast support
- Reduced motion preferences

## 🧪 Testing

### Recommended Testing Stack

```bash
# Unit testing
npm install --save-dev jest @testing-library/react

# E2E testing
npm install --save-dev playwright

# Accessibility testing
npm install --save-dev @axe-core/react
```

### Test Structure

```
__tests__/
├── components/          # Component tests
├── pages/              # Page tests
├── utils/              # Utility tests
└── e2e/                # End-to-end tests
```

## 📦 Deployment

### Build Production

```bash
npm run build
npm run start
```

### Deployment Platforms

- **Vercel**: Recommended for Next.js apps
- **Netlify**: Static site deployment
- **AWS**: S3 + CloudFront
- **Docker**: Container deployment

### Performance Checklist

- [ ] Lighthouse score > 90
- [ ] Core Web Vitals passed
- [ ] Images optimized
- [ ] CSS/JS minified
- [ ] PWA requirements met

## 🔗 Integration

### API Integration

Ready for integration with the authentication service:

```typescript
// Example API call structure
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
```

### Service Worker

Automatic caching for:
- Static assets (images, fonts, etc.)
- API responses (content, summaries)
- Offline fallbacks

## 🎨 Customization

### Brand Colors

Update `tailwind.config.js` to match your brand:

```javascript
colors: {
  primary: {
    50: '#eff6ff',
    // ... your brand colors
    950: '#172554',
  }
}
```

### Animations

Custom animations in `globals.css`:

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Build Errors**: Check TypeScript types and imports
2. **Styling Issues**: Verify Tailwind class names
3. **Performance**: Use Next.js built-in optimization
4. **PWA**: Check manifest.json and service worker

### Debug Mode

```bash
# Enable debug logging
DEBUG=next:* npm run dev

# TypeScript checking
npm run type-check
```

## 🤝 Contributing

1. Follow existing code style
2. Add TypeScript types for new features
3. Ensure responsive design
4. Test accessibility features
5. Update documentation

## 📄 License

MIT License - see LICENSE file for details