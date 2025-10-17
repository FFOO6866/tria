/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable standalone output for Docker builds
  output: 'standalone',
  // Experimental features disabled for simpler setup
  // experimental: {
  //   reactCompiler: true,
  // },
}

module.exports = nextConfig
