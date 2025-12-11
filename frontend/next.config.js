const path = require('path');
const { loadEnvConfig } = require('@next/env');

// Load env from root directory
const projectDir = path.resolve(__dirname, '..');
loadEnvConfig(projectDir);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || 'ResumeMatch AI',
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
  },
  async rewrites() {
    return {
      beforeFiles: [
        // Proxy only /api/process and similar backend routes, NOT /api/auth
        {
          source: '/api/process',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/process`,
        },
        {
          source: '/api/upload',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/upload`,
        },
        {
          source: '/api/status/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/status/:path*`,
        },
        {
          source: '/api/download/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/download/:path*`,
        },
      ],
    }
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
  },
}

module.exports = nextConfig

