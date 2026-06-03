import { Suspense } from "react";
import { AuthVerifyEmail } from "@/components/auth-verify-email";

export const dynamic = "force-dynamic";

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <AuthVerifyEmail />
    </Suspense>
  );
}
