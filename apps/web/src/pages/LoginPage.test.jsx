import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/auth-store";

import { LoginPage } from "./LoginPage";

const signIn = vi.fn();

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<h1>Dashboard loaded</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    signIn.mockReset();
    useAuthStore.setState({ status: "anonymous", user: null, signIn });
  });

  it("validates an incomplete login before it calls the authentication service", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(signIn).not.toHaveBeenCalled();
  });

  it("submits valid credentials and continues to the protected destination", async () => {
    const user = userEvent.setup();
    signIn.mockResolvedValue({ id: "1", display_name: "Ada", email: "ada@example.com" });
    renderLogin();

    await user.type(screen.getByLabelText("Email address"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "SecureCodePilot9");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(signIn).toHaveBeenCalledWith({ email: "ada@example.com", password: "SecureCodePilot9" });
    expect(await screen.findByRole("heading", { name: "Dashboard loaded" })).toBeInTheDocument();
  });
});
