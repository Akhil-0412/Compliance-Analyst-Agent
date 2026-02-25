import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: "http://127.0.0.1:8085/api/:path*",
        },
      ];
    }
    const backendUrl = process.env.Backend_URL || "https://akhil-008-agentic-compliance-analyst.hf.space";
    return [
      {
        source: "/api/analyze",
        destination: `${backendUrl}/api/chat`,
      },
      {
        source: "/api/chat/stream",
        destination: `${backendUrl}/api/chat/stream`,
      },
    ];
  },
};

export default nextConfig;
