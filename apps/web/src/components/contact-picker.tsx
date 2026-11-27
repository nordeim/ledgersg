"use client";

import * as React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { useContacts, type Contact } from "@/hooks/use-contacts";

/**
 * P9/B-3: a searchable contact picker — the Receive/Make payment forms
 * previously bound `contact_id` to a raw text input (UUID-validated), so a
 * user could not select a customer at all (no contacts page exists; the
 * UUID is unknowable through the UI).
 *
 * Debounced server-side search through the real list endpoint
 * (?search=&is_customer= / ?search=&is_supplier=); the selected contact's
 * id flows to the form via onChange.
 *
 * P19/FE-M2: the full WAI-ARIA 1.0 combobox pattern (the P16/P17/P18
 * deferred register's oldest item): the input controls the listbox
 * (aria-controls + aria-haspopup + aria-autocomplete), the active option
 * is announced via aria-activedescendant with aria-selected reflecting
 * it, and the keyboard contract (ArrowDown/Up with wrap, Enter to
 * select, Escape to close, Home/End) is implemented on the input — a
 * keyboard-only user can pick a customer on the payment/invoice forms.
 */

interface ContactPickerProps {
  orgId: string;
  type: "customer" | "supplier";
  value: string;
  onChange: (contactId: string) => void;
  /** P21/FE-L2: id of a visible label element — when given, it becomes
   * the combobox's accessible name (aria-labelledby outranks the
   * built-in aria-label, so the visible label is what SR users hear). */
  labelId?: string;
  /** P10/H-1: optional full-contact callback — the invoice form mirrors
   * the picked contact's name into its own form state (its zod schema
   * requires customer.name) without re-fetching the row. */
  onSelect?: (contact: Contact) => void;
  disabled?: boolean;
  invalid?: boolean;
}

export function ContactPicker({
  orgId,
  type,
  value,
  onChange,
  onSelect,
  labelId,
  disabled = false,
  invalid = false,
}: ContactPickerProps) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Contact | null>(null);
  /** P19/FE-M2: the roving active option (index into results, -1 = none). */
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  // React.useId: stable, SSR-safe, and pure (Math.random during render
  // trips the React Compiler's purity rule).
  const reactId = React.useId();
  const listboxId = `contact-picker-listbox${reactId.replace(/[^a-zA-Z0-9-]/g, "")}`;
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce the search so typing doesn't hammer the endpoint per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onClickAway = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener("mousedown", onClickAway);
    return () => document.removeEventListener("mousedown", onClickAway);
  }, []);

  // P26: useContacts returns the full envelope ({results, count}) —
  // the picker keeps the unpaginated shape (its search-bounded fetch
  // needs no page) and reads the results key.
  const { data, isLoading } = useContacts(orgId, {
    search: debounced || undefined,
    ...(type === "customer" ? { is_customer: true } : { is_supplier: true }),
    is_active: true,
  });

  const results = useMemo(() => data?.results ?? [], [data]);

  // A controlled value (e.g. a prefilled deep link, P9/B-3b) must display
  // its contact even before the user searches: derive it from the loaded
  // list when no explicit selection has been made.
  const effectiveSelected = useMemo(
    () => selected ?? results.find((c) => c.id === value) ?? null,
    [selected, results, value]
  );

  const handleSelect = (contact: Contact) => {
    setSelected(contact);
    onChange(contact.id);
    onSelect?.(contact);
    setOpen(false);
    setActiveIndex(-1);
    setQuery("");
  };

  const handleClear = () => {
    setSelected(null);
    onChange("");
    setQuery("");
    setActiveIndex(-1);
  };

  // Derived clamp (no effect): when the search narrows the results, an
  // out-of-range roving index reads as "none active" on the very next
  // render — the keydown handler re-establishes a valid index.
  const clampedIndex = activeIndex < results.length ? activeIndex : -1;

  const optionId = (index: number) => `${listboxId}-option-${index}`;

  /** P19/FE-M2: the combobox keyboard contract on the input. */
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!open) {
        setOpen(true);
        setActiveIndex(e.key === "ArrowDown" ? 0 : results.length - 1);
      } else if (results.length > 0) {
        // Wrap-around roving per the WAI-ARIA 1.0 pattern.
        setActiveIndex((idx) =>
          e.key === "ArrowDown"
            ? (idx + 1) % results.length
            : (idx <= 0 ? results.length : idx) - 1
        );
      }
      e.preventDefault();
    } else if (e.key === "Home" && open && results.length > 0) {
      setActiveIndex(0);
      e.preventDefault();
    } else if (e.key === "End" && open && results.length > 0) {
      setActiveIndex(results.length - 1);
      e.preventDefault();
    } else if (e.key === "Enter") {
      if (open && clampedIndex >= 0 && results[clampedIndex]) {
        handleSelect(results[clampedIndex]);
        e.preventDefault();
      }
    } else if (e.key === "Escape") {
      if (open) {
        setOpen(false);
        setActiveIndex(-1);
        e.preventDefault();
        e.stopPropagation();
      }
    }
  };

  const activeDescendant =
    open && clampedIndex >= 0 && results[clampedIndex]
      ? optionId(clampedIndex)
      : undefined;

  return (
    <div ref={wrapperRef} className="relative">
      {effectiveSelected ? (
        <div className="flex items-center justify-between h-10 w-full rounded-sm border border-border bg-surface px-3 py-2">
          <div className="text-sm text-text-primary truncate">
            <span className="font-medium">{effectiveSelected.name}</span>
            {effectiveSelected.email ? (
              <span className="text-text-muted"> · {effectiveSelected.email}</span>
            ) : null}
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={handleClear}
              aria-label={`Clear ${type}`}
              className="text-text-muted hover:text-text-primary"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="relative">
            <Search
              className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
              aria-hidden
            />
            <Input
              ref={inputRef}
              placeholder={`Search ${type}s by name…`}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setOpen(true);
                setActiveIndex(-1);
              }}
              onFocus={() => setOpen(true)}
              onBlur={() => {
                // P19/FE-M2: the listbox options are pointer-clicked
                // before the blur lands (mousedown precedes blur), so a
                // synchronous close would beat the selection.
                // P20/FE-M1: but Tab-away MUST dismiss (the WAI-ARIA
                // pattern — a dangling open listbox overlays the next
                // form fields and announces an expanded listbox owned by
                // an unfocused control). Defer one frame: if focus has
                // genuinely left the wrapper, close; if the mousedown
                // selection moved focus within (or the click lands
                // first), the guard holds the box open for it.
                requestAnimationFrame(() => {
                  if (
                    wrapperRef.current &&
                    !wrapperRef.current.contains(document.activeElement)
                  ) {
                    setOpen(false);
                    setActiveIndex(-1);
                  }
                });
              }}
              onKeyDown={handleInputKeyDown}
              disabled={disabled}
              aria-invalid={invalid}
              className="rounded-sm pl-9"
              role="combobox"
              aria-expanded={open}
              aria-label={`Search ${type}`}
              aria-labelledby={labelId}
              aria-haspopup="listbox"
              aria-autocomplete="list"
              aria-controls={listboxId}
              aria-activedescendant={activeDescendant}
            />
            {isLoading && (
              <Loader2
                className="h-4 w-4 absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-text-muted"
                aria-hidden
              />
            )}
          </div>
          {open && (
            <ul
              id={listboxId}
              role="listbox"
              aria-label={`${type} results`}
              className="absolute z-20 left-0 right-0 mt-1 max-h-56 overflow-auto rounded-sm border border-border bg-carbon shadow-lg"
            >
              {results.length === 0 ? (
                <li aria-hidden="true" className="px-3 py-3 text-sm text-text-secondary">
                  {debounced
                    ? `No ${type}s match “${debounced}”.`
                    : `Start typing to search your ${type}s.`}
                </li>
              ) : (
                results.map((contact, index) => {
                  const isActive = index === clampedIndex;
                  return (
                    <li
                      key={contact.id}
                      id={optionId(index)}
                      role="option"
                      aria-selected={isActive}
                      tabIndex={-1}
                      onMouseDown={(e) => {
                        // mousedown (not click): fires before the input's
                        // blur so the pointer selection never races the
                        // click-away close.
                        e.preventDefault();
                        handleSelect(contact);
                      }}
                      className={cn(
                        "px-3 py-2 text-sm text-text-primary cursor-pointer transition-colors",
                        isActive ? "bg-surface" : "hover:bg-surface"
                      )}
                    >
                      <span className="font-medium">{contact.name}</span>
                      {contact.email ? (
                        <span className="text-text-muted"> · {contact.email}</span>
                      ) : null}
                    </li>
                  );
                })
              )}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
