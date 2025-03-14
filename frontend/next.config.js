/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['localhost'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*', // バックエンドAPIへのプロキシ
      },
      {
        source: '/storage/:path*',
        destination: 'http://localhost:8000/storage/:path*', // バックエンドのストレージへのプロキシ
      },
    ]
  },
}

module.exports = nextConfig 