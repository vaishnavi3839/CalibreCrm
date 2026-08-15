import { LoginClient } from "./LoginClient";

/** Never cache login — NEXT_PUBLIC / Google button must reflect the latest build. */
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function LoginPage() {
  return <LoginClient />;
}
