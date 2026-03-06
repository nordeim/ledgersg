"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Upload, X, FileCheck, AlertCircle } from "lucide-react";
import { useImportBankTransactions, useBankAccounts } from "@/hooks/use-banking";

interface ImportTransactionsFormProps {
  orgId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ImportTransactionsForm({
  orgId,
  onSuccess,
  onCancel,
}: ImportTransactionsFormProps) {
  const { data: accountsData, isLoading: isLoadingAccounts } = useBankAccounts(orgId, {
    is_active: true,
  });
  const importMutation = useImportBankTransactions(orgId);

  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    imported: number;
    duplicates: number;
    errors?: Array<{ row: number; message: string }>;
  } | null>(null);

  const bankAccounts = accountsData?.results || [];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleImport = async () => {
    setError(null);

    // Validation
    if (!selectedAccountId) {
      setError("Please select a bank account");
      return;
    }

    if (!selectedFile) {
      setError("Please select a CSV file");
      return;
    }

    try {
      const response = await importMutation.mutateAsync({
        bank_account_id: selectedAccountId,
        file: selectedFile,
      });

      setResult(response);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    }
  };

  const handleReset = () => {
    setSelectedAccountId("");
    setSelectedFile(null);
    setError(null);
    setResult(null);
  };

  // Show results view
  if (result) {
    return (
      <Card className="border-border bg-carbon rounded-sm w-full max-w-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Import Results
          </CardTitle>
          <Button variant="ghost" size="icon" onClick={onCancel}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2 text-success">
            <FileCheck className="h-5 w-5" />
            <span>{result.imported} transactions imported</span>
          </div>
          
          {result.duplicates > 0 && (
            <div className="text-text-muted">
              {result.duplicates} duplicates skipped
            </div>
          )}

          {result.errors && result.errors.length > 0 && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {result.errors.length} errors occurred
              </AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2 pt-4">
            <Button variant="outline" onClick={handleReset}>
              Import Another
            </Button>
            <Button onClick={onCancel}>Close</Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-carbon rounded-sm w-full max-w-lg">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="font-display text-lg text-text-primary">
          Import Bank Statement
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={onCancel}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Bank Account Select */}
        <div className="space-y-2">
          <label className="text-sm text-text-secondary" htmlFor="bank-account">
            Bank Account
          </label>
          <Select
            value={selectedAccountId}
            onValueChange={setSelectedAccountId}
            disabled={isLoadingAccounts}
          >
            <SelectTrigger id="bank-account">
              <SelectValue placeholder="Select account" />
            </SelectTrigger>
            <SelectContent>
              {bankAccounts.map((account) => (
                <SelectItem key={account.id} value={account.id}>
                  {account.account_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* File Upload */}
        <div className="space-y-2">
          <label className="text-sm text-text-secondary" htmlFor="csv-file">
            CSV File
          </label>
          <div className="border-2 border-dashed border-border rounded-sm p-6 text-center">
            <input
              id="csv-file"
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <label
              htmlFor="csv-file"
              className="cursor-pointer flex flex-col items-center gap-2"
            >
              <Upload className="h-8 w-8 text-text-muted" />
              <span className="text-text-secondary">
                {selectedFile ? selectedFile.name : "Click to upload CSV file"}
              </span>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        <Button
          onClick={handleImport}
          disabled={importMutation.isPending || !selectedAccountId || !selectedFile}
          className="bg-accent-primary text-void hover:bg-accent-primary-dim"
        >
          {importMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Importing...
              </>
            ) : (
              "Import"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
