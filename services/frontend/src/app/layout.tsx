import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Updater - AI-Powered Content Aggregation',
  description: 'Transform information overload into actionable insights with AI-powered content summaries and audio briefings.',
  keywords: ['ai', 'content', 'aggregation', 'summaries', 'newsletters', 'productivity'],
  authors: [{ name: 'Updater Team' }],
  creator: 'Updater',
  publisher: 'Updater',
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: '/',
    title: 'Updater - AI-Powered Content Aggregation',
    description: 'Transform information overload into actionable insights with AI-powered content summaries and audio briefings.',
    siteName: 'Updater',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Updater - AI-Powered Content Aggregation',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Updater - AI-Powered Content Aggregation',
    description: 'Transform information overload into actionable insights with AI-powered content summaries and audio briefings.',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
  verification: {
    google: process.env.GOOGLE_VERIFICATION,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={inter.className}>
        <div id="root">
          {children}
        </div>
      </body>
    </html>
  );
}