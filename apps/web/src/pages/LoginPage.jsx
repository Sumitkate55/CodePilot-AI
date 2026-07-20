import { ArrowRight, LoaderCircle, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/features/auth/auth-store";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

export function LoginPage() {
  const signIn = useAuthStore((state) => state.signIn);
  const status = useAuthStore((state) => state.status);
  const location = useLocation();
  const navigate = useNavigate();
  const [submissionError, setSubmissionError] = useState("");
  const destination = location.state?.from ?? "/dashboard";
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (values) => {
    setSubmissionError("");
    try {
      await signIn(values);
      navigate(destination, { replace: true });
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : "Unable to sign in.");
    }
  };

  return (
    <article className="w-full">
      <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
        <ShieldCheck className="size-5" aria-hidden="true" />
      </span>
      <h1 className="mt-6 text-3xl font-semibold tracking-tight">Welcome back</h1>
      <p className="mt-3 leading-6 text-muted-foreground">Sign in to continue to your CodePilot workspace.</p>
      <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
        <label className="grid gap-2 text-sm font-medium" htmlFor="login-email">
          Email address
          <Input
            id="login-email"
            type="email"
            autoComplete="email"
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "login-email-error" : undefined}
            {...register("email")}
          />
          {errors.email ? <span id="login-email-error" className="text-xs text-red-600">{errors.email.message}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-medium" htmlFor="login-password">
          Password
          <Input
            id="login-password"
            type="password"
            autoComplete="current-password"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "login-password-error" : undefined}
            {...register("password")}
          />
          {errors.password ? <span id="login-password-error" className="text-xs text-red-600">{errors.password.message}</span> : null}
        </label>
        {submissionError ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{submissionError}</p> : null}
        <Button className="w-full" size="lg" type="submit" disabled={isSubmitting}>
          {isSubmitting ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <ArrowRight className="size-4" aria-hidden="true" />}
          {isSubmitting ? "Signing in" : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        New to CodePilot?{" "}
        <Link className="font-medium text-primary hover:underline" to="/register" state={{ from: destination }}>
          Create an account
        </Link>
      </p>
    </article>
  );
}
