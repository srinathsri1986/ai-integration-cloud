import { Suspense } from "react";
import { AuthResetPasswordForm } from "@/components/auth-reset-password-form";

export const dynamic = "force-dynamic";

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <AuthResetPasswordForm />
    </Suspense>
  );
}
