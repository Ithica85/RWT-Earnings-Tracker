/** @type {import('next').NextConfig} */
const nextConfig = {
  // The whole site is generated from JSON at build time — there is no
  // database and no request-time data fetching, so it exports statically.
  output: "export",
};

export default nextConfig;
