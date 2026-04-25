// Widget shell sizing constants. Extracted from Widget.jsx so the component
// file can satisfy react-refresh/only-export-components (HMR fast-refresh
// requires a module to export only components).

export const WIDGET_SIZES = {
  compact: { width: 320, height: 300 },
  standard: { width: 420, height: 480 },
  expanded: { width: 560, height: 620 },
}

export const WIDGET_MIN_W = 320
export const WIDGET_MIN_H = 300
