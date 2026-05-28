import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@netsuite-cfo/shared"]
};

export default nextConfig;
