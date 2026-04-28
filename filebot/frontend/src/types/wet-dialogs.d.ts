/**
 * Global WET-BOEW dialog functions from wet-dialogs.js
 * These are exposed on `window` by the wet-dialogs.js IIFE.
 */

interface Window {
  /**
   * Shows an informational alert modal. Returns a Promise that resolves
   * when the user dismisses it.
   */
  showWetAlert(message: string): Promise<void>;

  /**
   * Shows a confirmation dialog with Yes/No buttons.
   * Returns a Promise that resolves to `true` if user clicked Yes,
   * `false` if user clicked No or dismissed.
   *
   * May also be called via the alias: `window.showWetConfirm(message)`
   */
  wetYesOrNo(message: string, title?: string): Promise<boolean>;

  /**
   * Alias for wetYesOrNo, provided for backward compatibility.
   */
  showWetConfirm: (message: string, title?: string) => Promise<boolean>;
}
