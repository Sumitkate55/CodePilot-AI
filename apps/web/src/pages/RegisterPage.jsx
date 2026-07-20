import { ArrowRight, LoaderCircle, UserRoundPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/features/auth/auth-store";

const passwordSchema = z
  .string()
  .min(12, "Use at least 12 characters.")
  .regex(/[a-z]/, "Include a lowercase letter.")
  .regex(/[A-Z]/, "Include an uppercase letter.")
  .regex(/[0-9]/, "Include a number.");

const registerSchema = z
  .object({
    display_name: z.string().trim().min(2, "Enter at least 2 characters.").max(100),
    email: z.string().trim().email("Enter a valid email address."),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords do not match.",
    path: ["confirmPassword"],
  });

export function RegisterPage() {
  const signUp = useAuthStore((state) => state.signUp);
  const status = useAuthStore((state) => state.status);
  const location = useLocation();
  const navigate = useNavigate();
  const [submissionError, setSubmissionError] = useState("");
  const destination = location.state?.from ?? "/dashboard";
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { display_name: "", email: "", password: "", confirmPassword: "" },
  });

  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (values) => {
    setSubmissionError("");
    try {
      const account = {
        display_name: values.display_name,
        email: values.email,
        password: values.password,
      };
      await signUp(account);
      navigate(destination, { replace: true });
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : "Unable to create your account.");
    }
  };

  return (
    <article className="w-full">
      <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
        <UserRoundPlus className="size-5" aria-hidden="true" />
      </span>
      <h1 className="mt-6 text-3xl font-semibold tracking-tight">Create your workspace</h1>
      <p className="mt-3 leading-6 text-muted-foreground">Start exploring the systems behind your code.</p>
      <form className="mt-8 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <FormField id="display-name" label="Display name" error={errors.display_name?.message}>
          <Input id="display-name" autoComplete="name" aria-invalid={Boolean(errors.display_name)} {...register("display_name")} />
        </FormField>
        <FormField id="register-email" label="Email address" error={errors.email?.message}>
          <Input id="register-email" type="email" autoComplete="email" aria-invalid={Boolean(errors.email)} {...register("email")} />
        </FormField>
        <FormField id="register-password" label="Password" error={errors.password?.message}>
          <Input id="register-password" type="password" autoComplete="new-password" aria-invalid={Boolean(errors.password)} {...register("password")} />
        </FormField>
        <FormField id="confirm-password" label="Confirm password" error={errors.confirmPassword?.message}>
          <Input id="confirm-password" type="password" autoComplete="new-password" aria-invalid={Boolean(errors.confirmPassword)} {...register("confirmPassword")} />
        </FormField>
        {submissionError ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{submissionError}</p> : null}
        <Button className="w-full" size="lg" type="submit" disabled={isSubmitting}>
          {isSubmitting ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <ArrowRight className="size-4" aria-hidden="true" />}
          {isSubmitting ? "Creating account" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link className="font-medium text-primary hover:underline" to="/login" state={{ from: destination }}>
          Sign in
        </Link>
      </p>
    </article>
  );
}

function FormField({ id, label, error, children }) {
  const errorId = error ? `${id}-error` : undefined;
  return (
    <label className="grid gap-2 text-sm font-medium" htmlFor={id}>
      {label}
      {children}
      {error ? <span id={errorId} className="text-xs text-red-600">{error}</span> : null}
    </label>
  );
}
