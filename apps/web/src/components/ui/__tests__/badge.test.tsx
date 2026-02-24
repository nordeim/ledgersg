/**
 * LEDGERSG BADGE COMPONENT TESTS
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@/__tests__/utils";
import { Badge } from "../badge";

describe("Badge Component", () => {
  describe("Rendering", () => {
    it("renders with text content", () => {
      render(<Badge>Status</Badge>);

      expect(screen.getByText(/status/i)).toBeInTheDocument();
    });

    it("renders with custom className", () => {
      render(<Badge className="custom-badge">Custom</Badge>);

      const badge = screen.getByText(/custom/i);
      expect(badge).toHaveClass("custom-badge");
    });
  });

  describe("Variants", () => {
    it("renders default variant", () => {
      render(<Badge>Default</Badge>);

      const badge = screen.getByText(/default/i);
      expect(badge.className).toContain("bg-accent-primary");
    });

    it("renders secondary variant", () => {
      render(<Badge variant="secondary">Secondary</Badge>);

      const badge = screen.getByText(/secondary/i);
      expect(badge.className).toContain("bg-accent-secondary");
    });

    it("renders destructive variant", () => {
      render(<Badge variant="destructive">Destructive</Badge>);

      const badge = screen.getByText(/destructive/i);
      expect(badge.className).toContain("bg-alert");
    });

    it("renders outline variant", () => {
      render(<Badge variant="outline">Outline</Badge>);

      const badge = screen.getByText(/outline/i);
      expect(badge.className).toContain("border-border");
    });
  });

  describe("Styling", () => {
    it("has rounded corners", () => {
      render(<Badge>Rounded</Badge>);

      const badge = screen.getByText(/rounded/i);
      expect(badge.className).toContain("rounded-sm");
    });

    it("is inline-flex", () => {
      render(<Badge>Inline</Badge>);

      const badge = screen.getByText(/inline/i);
      expect(badge.className).toContain("inline-flex");
    });
  });
});
