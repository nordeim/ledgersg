/**
 * LEDGERSG INPUT COMPONENT TESTS
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@/__tests__/utils";
import { Input } from "../input";

describe("Input Component", () => {
  describe("Rendering", () => {
    it("renders with default props", () => {
      render(<Input placeholder="Enter text" />);

      expect(screen.getByPlaceholderText(/enter text/i)).toBeInTheDocument();
    });

    it("renders with label", () => {
      render(<Input label="Email" id="email" />);

      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });

    it("renders with error message", () => {
      render(<Input error="This field is required" />);

      expect(screen.getByText(/this field is required/i)).toBeInTheDocument();
    });

    it("renders with helper text via aria-describedby", () => {
      render(
        <>
          <Input aria-describedby="helper" placeholder="With helper" />
          <span id="helper">We will never share your email</span>
        </>
      );

      expect(screen.getByText(/we will never share your email/i)).toBeInTheDocument();
    });
  });

  describe("States", () => {
    it("handles disabled state", () => {
      render(<Input disabled placeholder="Disabled" />);

      const input = screen.getByPlaceholderText(/disabled/i);
      expect(input).toBeDisabled();
      expect(input.className).toContain("disabled:cursor-not-allowed");
    });

    it("handles required attribute", () => {
      render(<Input required placeholder="Required" />);

      const input = screen.getByPlaceholderText(/required/i);
      expect(input).toHaveAttribute("required");
    });

    it("applies error styling when error prop is provided", () => {
      render(<Input error="Error message" placeholder="Error" />);

      const input = screen.getByPlaceholderText(/error/i);
      expect(input.className).toContain("border-alert");
    });
  });

  describe("Interactions", () => {
    it("calls onChange when value changes", () => {
      const handleChange = vi.fn();
      render(<Input onChange={handleChange} placeholder="Type here" />);

      const input = screen.getByPlaceholderText(/type here/i);
      fireEvent.change(input, { target: { value: "test value" } });

      expect(handleChange).toHaveBeenCalled();
    });

    it("calls onFocus when focused", () => {
      const handleFocus = vi.fn();
      render(<Input onFocus={handleFocus} placeholder="Focus me" />);

      const input = screen.getByPlaceholderText(/focus me/i);
      fireEvent.focus(input);

      expect(handleFocus).toHaveBeenCalled();
    });

    it("calls onBlur when blurred", () => {
      const handleBlur = vi.fn();
      render(<Input onBlur={handleBlur} placeholder="Blur me" />);

      const input = screen.getByPlaceholderText(/blur me/i);
      fireEvent.blur(input);

      expect(handleBlur).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("has correct input role", () => {
      render(<Input placeholder="Accessible input" />);

      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("associates label with input via htmlFor", () => {
      render(<Input label="Username" id="username" />);

      const label = screen.getByText(/username/i);
      expect(label).toHaveAttribute("for", "username");
    });

    it("has aria-invalid when error is present", () => {
      render(<Input error="Invalid" placeholder="Invalid" />);

      const input = screen.getByPlaceholderText(/invalid/i);
      expect(input).toHaveAttribute("aria-invalid", "true");
    });

    it("has aria-describedby linking to error message", () => {
      render(<Input error="Error description" id="test-input" />);

      const input = screen.getByRole("textbox");
      expect(input).toHaveAttribute("aria-describedby", "test-input-error");
    });

    it("supports aria-label", () => {
      render(<Input aria-label="Search input" placeholder="Search" />);

      expect(screen.getByLabelText(/search input/i)).toBeInTheDocument();
    });
  });

  describe("Types", () => {
    it("renders text input by default (no type attribute)", () => {
      render(<Input placeholder="Text" />);

      const input = screen.getByPlaceholderText(/text/i);
      // Default HTML input type is text when not specified
      expect(input).toBeInTheDocument();
    });

    it("renders password input", () => {
      render(<Input type="password" placeholder="Password" />);

      const input = screen.getByPlaceholderText(/password/i);
      expect(input).toHaveAttribute("type", "password");
    });

    it("renders email input", () => {
      render(<Input type="email" placeholder="Email" />);

      const input = screen.getByPlaceholderText(/email/i);
      expect(input).toHaveAttribute("type", "email");
    });

    it("renders number input", () => {
      render(<Input type="number" placeholder="Number" />);

      const input = screen.getByPlaceholderText(/number/i);
      expect(input).toHaveAttribute("type", "number");
    });
  });
});
