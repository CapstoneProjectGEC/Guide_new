import React, { useState, useEffect, useRef } from "react";
import {
  FileText,
  Upload,
  Download,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Search,
  Copy,
  Check,
  Loader2,
  Lock,
} from "lucide-react";
import { adminApiClient } from "@/services/adminApi";
import { authService } from "@/services/auth";
import { DocumentItem } from "@/types/api";

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

export const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentItem | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const canCurate = authService.hasRole("SITE_CURATOR");

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const res = await adminApiClient.listDocuments(100, 0);
      setDocuments(res.documents);
      setTotalCount(res.total);
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to retrieve documents list.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    // 1. Frontend validation: File extension
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setNotification({
        type: "error",
        message: "Invalid file type. Only authentic PDF documents (.pdf) are permitted.",
      });
      return;
    }

    // 2. Frontend validation: File size limit (50MB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setNotification({
        type: "error",
        message: `File size exceeds the 50MB threshold (${(file.size / (1024 * 1024)).toFixed(1)}MB).`,
      });
      return;
    }

    setIsUploading(true);
    setNotification(null);

    try {
      const uploadedDoc = await adminApiClient.uploadDocument(file);
      setNotification({
        type: "success",
        message: `Document '${uploadedDoc.filename}' ingested successfully (${uploadedDoc.page_count} pages).`,
      });
      await loadDocuments();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to upload document.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async (doc: DocumentItem) => {
    try {
      const blob = await adminApiClient.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || `Failed to download ${doc.filename}.`,
      });
    }
  };

  const handleDelete = async () => {
    if (!documentToDelete) return;
    setIsDeleting(true);
    try {
      await adminApiClient.deleteDocument(documentToDelete.id);
      setNotification({
        type: "success",
        message: `Document '${documentToDelete.filename}' removed from repository.`,
      });
      setDocumentToDelete(null);
      await loadDocuments();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || `Failed to delete ${documentToDelete.filename}.`,
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.sha256_hash.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header and Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <div>
          <h2 className="text-xl font-bold font-display text-heritage-brown dark:text-heritage-marble">
            Heritage Document Archive
          </h2>
          <p className="text-xs text-heritage-umber dark:text-heritage-stone mt-1">
            Official temple research PDFs, ASI monographs, and archaeological survey records.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            accept=".pdf"
            onChange={handleFileUpload}
            className="hidden"
            id="pdf-upload-input"
            disabled={!canCurate || isUploading}
          />

          {/* Upload Button */}
          {canCurate ? (
            <label
              htmlFor="pdf-upload-input"
              className={`inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-midnight-basalt shadow-xs cursor-pointer transition-colors ${
                isUploading ? "opacity-50 cursor-not-allowed pointer-events-none" : ""
              }`}
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Validating & Storing...</span>
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload PDF</span>
                </>
              )}
            </label>
          ) : (
            <div
              title="Upload requires SITE_CURATOR or higher role"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-carved-basalt text-heritage-umber dark:text-heritage-stone opacity-60 cursor-not-allowed"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Curator Required</span>
            </div>
          )}

          <button
            onClick={loadDocuments}
            disabled={isLoading}
            aria-label="Refresh document archive"
            className="p-2 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          role="alert"
          className={`p-3 rounded-lg text-xs flex items-center justify-between animate-in fade-in duration-200 ${
            notification.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-heritage-terracotta/10 border border-heritage-terracotta/30 text-heritage-terracotta dark:text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-xs underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Search and Count Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-heritage-umber dark:text-heritage-stone" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by filename or hash..."
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-heritage-brown/20 dark:border-heritage-gold/20 bg-white dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble placeholder-heritage-umber/60 focus:outline-hidden focus:ring-2 focus:ring-heritage-gold"
          />
        </div>
        <span className="text-xs text-heritage-umber dark:text-heritage-stone">
          Showing {filteredDocs.length} of {totalCount} documents
        </span>
      </div>

      {/* Documents Table */}
      <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-heritage-sandstone dark:bg-heritage-stone-dark/80 text-heritage-brown dark:text-heritage-marble font-semibold border-b border-heritage-brown/10 dark:border-heritage-gold/15">
                <th className="py-3 px-4">Document</th>
                <th className="py-3 px-4">Pages</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">SHA-256 Digest</th>
                <th className="py-3 px-4">Ingested At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-heritage-brown/5 dark:divide-heritage-gold/10">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-heritage-umber dark:text-heritage-stone">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-heritage-gold" />
                    <span>Loading documents from storage...</span>
                  </td>
                </tr>
              ) : filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-heritage-umber dark:text-heritage-stone">
                    No documents found matching current filter.
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-heritage-sandstone/30 dark:hover:bg-heritage-stone-dark/40 transition-colors"
                  >
                    <td className="py-3 px-4 font-medium text-heritage-brown dark:text-heritage-marble flex items-center gap-2">
                      <FileText className="w-4 h-4 text-heritage-gold flex-shrink-0" />
                      <span className="truncate max-w-[220px]" title={doc.filename}>
                        {doc.filename}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-heritage-umber dark:text-heritage-stone">
                      {doc.page_count}
                    </td>
                    <td className="py-3 px-4 text-heritage-umber dark:text-heritage-stone">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="py-3 px-4 text-heritage-umber dark:text-heritage-stone font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span title={doc.sha256_hash}>
                          {doc.sha256_hash.slice(0, 10)}...{doc.sha256_hash.slice(-6)}
                        </span>
                        <button
                          onClick={() => copyToClipboard(doc.sha256_hash, doc.id)}
                          aria-label={`Copy SHA-256 hash for ${doc.filename}`}
                          className="p-1 hover:text-heritage-gold transition-colors"
                        >
                          {copiedHash === doc.id ? (
                            <Check className="w-3 h-3 text-emerald-500" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-heritage-umber dark:text-heritage-stone">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleDownload(doc)}
                          aria-label={`Download ${doc.filename}`}
                          title="Download PDF"
                          className="p-1.5 rounded text-heritage-brown dark:text-heritage-marble hover:bg-heritage-sandstone dark:hover:bg-heritage-stone-dark hover:text-heritage-gold transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>

                        {canCurate && (
                          <button
                            onClick={() => setDocumentToDelete(doc)}
                            aria-label={`Delete ${doc.filename}`}
                            title="Delete Document"
                            className="p-1.5 rounded text-heritage-terracotta hover:bg-heritage-terracotta/10 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {documentToDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150"
        >
          <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/20 dark:border-heritage-gold/20 p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 text-heritage-terracotta mb-3">
              <AlertCircle className="w-6 h-6 flex-shrink-0" />
              <h3 id="delete-modal-title" className="text-base font-bold">
                Confirm Document Deletion
              </h3>
            </div>
            <p className="text-xs text-heritage-umber dark:text-heritage-stone leading-relaxed mb-4">
              Are you sure you want to permanently delete <strong>{documentToDelete.filename}</strong>? This action removes the physical PDF file from the server and deletes its metadata records.
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setDocumentToDelete(null)}
                disabled={isDeleting}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-heritage-terracotta text-white hover:bg-red-700 shadow-xs transition-colors disabled:opacity-50"
              >
                {isDeleting && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Delete Permanently</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
