/**
 * LEDGERSG BUTTON COMPONENT TESTS
 *
 * Tests all Button variants, sizes, states, and interactions
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@/__tests__/utils";
import { Button } from "../button";

describe("Button Component", () => {
  describe("Rendering", () => {
    it("renders with default props", () => {
      render(<Button>Click me</Button>);

      const button = screen.getByRole("button", { name: /click me/i });
      expect(button).toBeInTheDocument();
      expect(button).toHaveTextContent("Click me");
    });

    it("renders with custom className", () => {
      render(<Button className="custom-class">Button</Button>);

      const button = screen.getByRole("button");
      expect(button).toHaveClass("custom-class");
    });

    // Note: asChild functionality uses Radix UI Slot
    // This is tested by the Radix UI library itself
  });

  describe("Variants", () => {
    it("renders default variant with accent styling", () => {
      render(<Button>Default</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("bg-accent-primary");
    });

    it("renders destructive variant with alert styling", () => {
      render(<Button variant="destructive">Delete</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("bg-alert");
    });

    it("renders outline variant with border", () => {
      render(<Button variant="outline">Outline</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("border");
    });

    it("renders secondary variant", () => {
      render(<Button variant="secondary">Secondary</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });

    it("renders ghost variant", () => {
      render(<Button variant="ghost">Ghost</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });

    it("renders link variant", () => {
      render(<Button variant="link">Link</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("underline-offset-4");
    });
  });

  describe("Sizes", () => {
    it("renders default size", () => {
      render(<Button>Default Size</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });

    it("renders sm size", () => {
      render(<Button size="sm">Small</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });

    it("renders lg size", () => {
      render(<Button size="lg">Large</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });

    it("renders icon size", () => {
      render(<Button size="icon">★</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
    });
  });

  describe("States", () => {
    it("handles disabled state", () => {
      render(<Button disabled>Disabled</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });

    it("handles aria-disabled", () => {
      render(<Button aria-disabled>ARIA Disabled</Button>);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-disabled", "true");
    });

    it("handles aria-busy for loading state", () => {
      render(<Button aria-busy>Loading</Button>);

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-busy", "true");
    });
  });

  describe("Interactions", () => {
    it("calls onClick handler when clicked", () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click me</Button>);

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("does not call onClick when disabled", () => {
      const handleClick = vi.fn();
      render(
        <Button onClick={handleClick} disabled>
          Disabled
        </Button>
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(handleClick).not.toHaveBeenCalled();
    });

    it("is focusable", () => {
      render(<Button>Focusable</Button>);

      const button = screen.getByRole("button");
      button.focus();
      expect(button).toHaveFocus();
    });
  });

  describe("Accessibility", () => {
    it("has correct button role", () => {
      render(<Button>Accessible Button</Button>);

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("supports aria-label", () => {
      render(<Button aria-label="Close dialog">×</Button>);

      expect(screen.getByLabelText(/close dialog/i)).toBeInTheDocument();
    });

    it("supports aria-describedby", () => {
      render(
        <>
          <span id="desc">Button description</span>
          <Button aria-describedby="desc">Button</Button>
        </>
      );

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-describedby", "desc");
    });

    it("has focus visible styling", () => {
      render(<Button>Focus Style</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("focus-visible:ring-2");
    });
  });

  describe("Neo-Brutalist Design", () => {
    it("has square corners (rounded-sm)", () => {
      render(<Button>Brutalist</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("rounded-sm");
    });

    it("has focus ring with accent color", () => {
      render(<Button>Accent Focus</Button>);

      const button = screen.getByRole("button");
      expect(button.className).toContain("focus-visible:ring-accent-primary");
    });
  });
});
