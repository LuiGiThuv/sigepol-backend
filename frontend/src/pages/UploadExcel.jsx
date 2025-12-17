import React, { useRef, useState } from "react";
import * as XLSX from "xlsx";
import api from "../services/api";

export default function UploadExcel() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [previewSelectedSheet, setPreviewSelectedSheet] = useState(null);
  const fileRef = useRef(null);
  const previewRequestIdRef = useRef(0);

  const sanitizeCellValue = (value) => {
    if (value === undefined || value === null) {
      return "";
    }
    if (value instanceof Date) {
      return value.toISOString().split("T")[0];
    }
    return String(value);
  };

  const generatePreview = async (selectedFile) => {
    setPreview(null);
    setPreviewError(null);
    setPreviewSelectedSheet(null);
    if (!selectedFile) {
      return;
    }

    const requestId = previewRequestIdRef.current + 1;
    previewRequestIdRef.current = requestId;

    try {
      setPreviewLoading(true);
      const arrayBuffer = await selectedFile.arrayBuffer();
      const workbook = XLSX.read(arrayBuffer, { type: "array" });
      const sheets = workbook.SheetNames || [];

      const excelData = {
        sheets,
        data: {},
      };

      let totalFilas = 0;

      sheets.forEach((sheetName) => {
        const worksheet = workbook.Sheets[sheetName];
        if (!worksheet) {
          excelData.data[sheetName] = { headers: [], rows: [] };
          return;
        }

        const sheetMatrix = XLSX.utils.sheet_to_json(worksheet, {
          header: 1,
          raw: false,
          defval: "",
        });

        if (!sheetMatrix || sheetMatrix.length === 0) {
          excelData.data[sheetName] = { headers: [], rows: [] };
          return;
        }

        const headers = sheetMatrix[0].map((header) => sanitizeCellValue(header));
        const totalRowsSheet = Math.max(sheetMatrix.length - 1, 0);
        const rows = sheetMatrix.slice(1, 101).map((row) => {
          const normalizedRow = headers.map((_, index) => sanitizeCellValue(row[index]));
          return normalizedRow;
        });

        totalFilas += totalRowsSheet;

        excelData.data[sheetName] = {
          headers,
          rows,
          totalRows: totalRowsSheet,
        };
      });

      const previewData = {
        excel_data: excelData,
        total_hojas: sheets.length,
        total_filas: totalFilas,
      };

      if (previewRequestIdRef.current === requestId && fileRef.current === selectedFile) {
        setPreview(previewData);
        setPreviewSelectedSheet(sheets[0] || null);
        setPreviewError(null);
      }
    } catch (err) {
      console.error("Preview error:", err);
      if (previewRequestIdRef.current === requestId) {
        setPreviewError("No se pudo procesar el archivo Excel seleccionado.");
      }
    } finally {
      if (previewRequestIdRef.current === requestId) {
        setPreviewLoading(false);
      }
    }
  };

  const handleFileChange = (event) => {
    const selected = event.target.files?.[0];
    setFile(selected || null);
    fileRef.current = selected || null;
    setError(null);
    setResult(null);
    if (selected) {
      generatePreview(selected);
    } else {
      setPreview(null);
      setPreviewError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Selecciona un archivo Excel primero.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setError(null);
      const res = await api.post("/importaciones/upload-excel/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(res.data);
      setFile(null);
      fileRef.current = null;
      previewRequestIdRef.current = 0;
      setPreviewLoading(false);
      setPreview(null);
      setPreviewSelectedSheet(null);
      setPreviewError(null);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Error al subir archivo");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg rounded-xl mb-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-4xl font-bold mb-2">Cargar Pólizas</h1>
          <p className="text-blue-100 text-lg">Importa datos desde archivos Excel (.xlsx, .xls)</p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto">
        {/* Upload Zone */}
        <div className="bg-white p-8 rounded-xl shadow-lg mb-6">
          <div className="border-3 border-dashed border-blue-300 rounded-xl p-12 text-center hover:border-blue-500 transition-colors bg-gradient-to-br from-blue-50 to-indigo-50">
            <div className="mb-4 text-6xl">📁</div>
            <p className="text-slate-700 mb-2 font-semibold text-lg">Selecciona un archivo Excel</p>
            <p className="text-slate-600 text-sm mb-6">Formatos aceptados: .xlsx, .xls</p>
            <label className="inline-block">
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="hidden"
                aria-label="Seleccionar archivo Excel"
              />
              <span className="px-6 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:shadow-lg hover:shadow-blue-500/50 cursor-pointer inline-block font-semibold transition-all duration-200 transform hover:scale-105">
                Elegir archivo
              </span>
            </label>
            {file && (
              <p className="mt-4 text-green-600 font-semibold">✓ Archivo seleccionado: {file.name}</p>
            )}
          </div>

          {previewLoading && (
            <div className="mt-6 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg flex items-center justify-between">
              <div>
                <p className="font-semibold">Generando vista previa...</p>
                <p className="text-sm text-blue-600">Estamos leyendo las primeras filas del Excel seleccionado.</p>
              </div>
              <span className="text-3xl animate-spin">⏳</span>
            </div>
          )}

          {previewError && (
            <div className="mt-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              <p className="font-semibold">No se pudo generar la vista previa.</p>
              <p className="text-sm">{previewError}</p>
            </div>
          )}

          {preview && !previewLoading && (
            <div className="mt-6 bg-slate-50 border border-slate-200 rounded-xl p-5 shadow-inner">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-slate-800">Vista previa del Excel</h3>
                  <p className="text-sm text-slate-600">
                    Total estimado: {preview.total_filas} registros en {preview.total_hojas} hoja(s).
                    {previewSelectedSheet && preview.excel_data?.data?.[previewSelectedSheet] && (
                      (() => {
                        const sheetData = preview.excel_data.data[previewSelectedSheet];
                        const totalRowsSheet = sheetData.totalRows ?? sheetData.rows.length;
                        const displayed = sheetData.rows.length;
                        return ` Mostrando ${displayed} de ${totalRowsSheet} filas de la hoja "${previewSelectedSheet}".`;
                      })()
                    )}
                  </p>
                </div>
                <div className="flex gap-3 flex-wrap">
                  <div className="bg-white rounded-lg px-4 py-2 shadow border border-slate-200 text-center">
                    <p className="text-xs uppercase text-slate-500 font-semibold">Hojas</p>
                    <p className="text-xl font-bold text-slate-800">{preview.total_hojas}</p>
                  </div>
                  {previewSelectedSheet && preview.excel_data?.data?.[previewSelectedSheet] && (
                    <>
                      <div className="bg-white rounded-lg px-4 py-2 shadow border border-slate-200 text-center">
                        <p className="text-xs uppercase text-slate-500 font-semibold">Columnas</p>
                        <p className="text-xl font-bold text-slate-800">{preview.excel_data.data[previewSelectedSheet].headers.length}</p>
                      </div>
                      <div className="bg-white rounded-lg px-4 py-2 shadow border border-slate-200 text-center">
                        <p className="text-xs uppercase text-slate-500 font-semibold">Filas hoja</p>
                        <p className="text-xl font-bold text-slate-800">{preview.excel_data.data[previewSelectedSheet].totalRows ?? preview.excel_data.data[previewSelectedSheet].rows.length}</p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {preview.excel_data?.sheets?.length > 0 && (
                <div className="bg-slate-100 border border-slate-300 rounded-lg px-4 py-2 mb-4 flex flex-wrap gap-2">
                  {preview.excel_data.sheets.map((sheet) => (
                    <button
                      key={sheet}
                      onClick={() => setPreviewSelectedSheet(sheet)}
                      className={`px-4 py-2 rounded text-sm font-medium transition-all ${
                        previewSelectedSheet === sheet
                          ? 'bg-white text-green-700 border border-green-500 shadow'
                          : 'bg-slate-200 text-slate-600 hover:bg-slate-300 border border-transparent'
                      }`}
                    >
                      📄 {sheet}
                    </button>
                  ))}
                </div>
              )}

              <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
                {previewSelectedSheet && preview.excel_data?.data?.[previewSelectedSheet] ? (
                  (() => {
                    const sheetData = preview.excel_data.data[previewSelectedSheet];
                    const headers = sheetData.headers || [];
                    const rows = sheetData.rows || [];

                    if (headers.length === 0 || rows.length === 0) {
                      return (
                        <div className="p-8 text-center text-slate-600 text-sm">
                          La hoja seleccionada no contiene datos para mostrar.
                        </div>
                      );
                    }

                    return (
                      <div className="overflow-auto max-h-[60vh]">
                        <table className="w-full border-collapse" style={{ fontFamily: 'Arial, sans-serif', fontSize: '13px' }}>
                          <thead className="sticky top-0 bg-slate-200">
                            <tr>
                              <th className="bg-slate-300 border border-slate-400 px-2 py-1 text-center text-slate-600 font-semibold w-12">#</th>
                              {headers.map((header, idx) => (
                                <th
                                  key={idx}
                                  className="bg-slate-200 border border-slate-400 px-3 py-2 text-left text-slate-700 font-semibold whitespace-nowrap"
                                >
                                  {header}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {rows.map((row, rowIdx) => (
                              <tr key={rowIdx} className="hover:bg-blue-50">
                                <td className="bg-slate-100 border border-slate-300 px-2 py-1 text-center text-slate-600 font-semibold text-xs">
                                  {rowIdx + 1}
                                </td>
                                {row.map((cell, cellIdx) => (
                                  <td
                                    key={cellIdx}
                                    className="border border-slate-300 px-3 py-2 text-slate-800 whitespace-nowrap"
                                  >
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  })()
                ) : (
                  <div className="p-8 text-center text-slate-600 text-sm">
                    No encontramos filas para mostrar en la vista previa. Verifica que el Excel tenga datos.
                  </div>
                )}
              </div>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={loading || !file}
            className="w-full mt-6 px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-green-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
          >
            {loading ? "⏳ Procesando..." : "🚀 Subir archivo"}
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border-2 border-red-300 text-red-800 px-6 py-4 rounded-xl mb-6 font-medium animate-pulse">
            <p>⚠️ {error}</p>
          </div>
        )}

        {/* Success Result */}
        {result && (
          <div className="bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-300 rounded-xl p-6 shadow-lg">
            <h2 className="text-2xl font-bold text-green-800 mb-4">✓ Importación Completada</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-4 text-center">
                <p className="text-sm text-slate-600 font-semibold">Insertados</p>
                <p className="text-3xl font-bold text-green-600">{result.insertados || 0}</p>
              </div>
              <div className="bg-white rounded-lg p-4 text-center">
                <p className="text-sm text-slate-600 font-semibold">Actualizados</p>
                <p className="text-3xl font-bold text-blue-600">{result.actualizados || 0}</p>
              </div>
              <div className="bg-white rounded-lg p-4 text-center">
                <p className="text-sm text-slate-600 font-semibold">Errores</p>
                <p className="text-3xl font-bold text-red-600">{result.errores || 0}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

