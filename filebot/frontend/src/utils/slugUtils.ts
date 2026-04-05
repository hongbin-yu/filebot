/**
 * Slug utility functions for generating URL-friendly IDs
 */

/**
 * Convert a string to a URL-friendly slug
 * Rules:
 * 1. Convert to lowercase
 * 2. Replace spaces with '-'
 * 3. Replace French accented characters with English equivalents
 * 4. Remove special characters except hyphen and underscore
 * 5. Trim extra hyphens
 * 
 * @param text - The text to convert to slug
 * @returns URL-friendly slug
 */
export function toSlug(text: string): string {
  if (!text) return '';
  
  // Step 1: Convert to lowercase
  let slug = text.toLowerCase();
  
  // Step 2: Replace French accented characters with English equivalents
  slug = slug.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  
  // More comprehensive accented character replacement
  const accentsMap: { [key: string]: string } = {
    'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
    'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
    'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
    'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
    'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
    'ñ': 'n',
    'ç': 'c',
    'ÿ': 'y',
    'œ': 'oe', 'æ': 'ae',
    'ß': 'ss'
  };
  
  slug = slug.replace(/[^\u0000-\u007E]/g, (char) => accentsMap[char] || char);
  
  // Step 3: Replace spaces with hyphens
  slug = slug.replace(/\s+/g, '-');
  
  // Step 4: Remove special characters except hyphen and underscore
  slug = slug.replace(/[^a-z0-9-_]/g, '-');
  
  // Step 5: Trim extra hyphens
  slug = slug.replace(/-+/g, '-');
  slug = slug.replace(/^-+/, '');
  slug = slug.replace(/-+$/, '');
  
  return slug;
}

/**
 * Generate a unique slug with duplicate handling
 * If a slug already exists in the provided set, append incremental numbers
 * 
 * @param baseSlug - The base slug to start with
 * @param existingSlugs - Set of slugs that already exist
 * @param originalId - Original ID for uniqueness (optional)
 * @returns Unique slug
 */
export function generateUniqueSlug(
  baseSlug: string, 
  existingSlugs?: Set<string>, 
  originalId?: string
): string {
  // If no existing slugs to check, just return the base slug with optional ID
  if (!existingSlugs || existingSlugs.size === 0) {
    if (originalId) {
      const shortId = originalId.substring(0, 8);
      return `${baseSlug}-${shortId}`;
    }
    return baseSlug;
  }
  
  // Try the base slug first (with ID if provided)
  let candidate = baseSlug;
  if (originalId) {
    const shortId = originalId.substring(0, 8);
    candidate = `${baseSlug}-${shortId}`;
  }
  
  // If the candidate is unique, return it
  if (!existingSlugs.has(candidate)) {
    return candidate;
  }
  
  // If the candidate already exists (with ID), try without ID first
  if (originalId) {
    if (!existingSlugs.has(baseSlug)) {
      return baseSlug;
    }
  }
  
  // Try with incremental numbers
  let counter = 2;
  let numberedSlug = originalId 
    ? `${baseSlug}-${originalId.substring(0, 8)}-${counter}`
    : `${baseSlug}-${counter}`;
  
  while (existingSlugs.has(numberedSlug)) {
    counter++;
    numberedSlug = originalId
      ? `${baseSlug}-${originalId.substring(0, 8)}-${counter}`
      : `${baseSlug}-${counter}`;
  }
  
  return numberedSlug;
}

/**
 * Generate a slug from a folder name for use in URLs
 * Handles duplicate names by appending incremental numbers
 * 
 * @param folderName - The folder name
 * @param folderId - The original folder ID (for uniqueness)
 * @param existingSlugs - Optional set of existing slugs to avoid duplicates
 * @returns URL-friendly folder slug
 */
export function generateFolderSlug(
  folderName: string, 
  folderId?: string,
  existingSlugs?: Set<string>
): string {
  const baseSlug = toSlug(folderName);
  return generateUniqueSlug(baseSlug, existingSlugs, folderId);
}

/**
 * Generate a slug from a document title for use in URLs
 * Handles duplicate names by appending incremental numbers
 * 
 * @param documentTitle - The document title
 * @param documentId - The original document ID (for uniqueness)
 * @param existingSlugs - Optional set of existing slugs to avoid duplicates
 * @returns URL-friendly document slug
 */
export function generateDocumentSlug(
  documentTitle: string, 
  documentId?: string,
  existingSlugs?: Set<string>
): string {
  const baseSlug = toSlug(documentTitle);
  return generateUniqueSlug(baseSlug, existingSlugs, documentId);
}

/**
 * Generate a slug from a drawer name for use in URLs
 * Handles duplicate names by appending short ID (first 8 chars) only when necessary
 * Format preference:
 * 1. drawername (if no duplication and existingSlugs provided)
 * 2. drawername-xxxxxxxx (if name duplicates, or no existingSlugs info, where xxxxxxxx is first 8 chars of UUID without hyphens)
 * 3. drawername-xxxxxxxx-2 (if both name and short ID duplicate)
 * 
 * @param drawerName - The drawer name
 * @param drawerId - The original drawer ID (for uniqueness)
 * @param existingSlugs - Optional set of existing slugs to avoid duplicates
 * @returns URL-friendly drawer slug
 */
export function generateDrawerSlug(
  drawerName: string, 
  drawerId?: string,
  existingSlugs?: Set<string>
): string {
  const baseSlug = toSlug(drawerName);
  
  // If no drawerId provided, use base slug with duplicate handling
  if (!drawerId) {
    // Fallback to generateUniqueSlug without ID
    return generateUniqueSlug(baseSlug, existingSlugs);
  }
  
  // Get short ID (first 8 characters of the UUID without hyphens)
  const shortId = drawerId.replace(/-/g, '').substring(0, 8);
  const slugWithShortId = `${baseSlug}-${shortId}`;
  
  // If no existing slugs to check, prefer base slug for cleaner URLs
  // We can look up by slug in the database instead of extracting ID from slug
  if (!existingSlugs || existingSlugs.size === 0) {
    return baseSlug; // Return clean name-only slug when no duplication info available
  }
  
  // Strategy 1: Try base slug (drawername only) if not duplicated
  if (!existingSlugs.has(baseSlug)) {
    return baseSlug;
  }
  
  // Strategy 2: Try slug with short ID if base slug is duplicated
  if (!existingSlugs.has(slugWithShortId)) {
    return slugWithShortId;
  }
  
  // Strategy 3: If both base slug and slug with short ID exist, add incremental numbers
  let counter = 2;
  let numberedSlug = `${baseSlug}-${shortId}-${counter}`;
  
  while (existingSlugs.has(numberedSlug)) {
    counter++;
    numberedSlug = `${baseSlug}-${shortId}-${counter}`;
  }
  
  return numberedSlug;
}

/**
 * Generate a slug from an application name for use in URLs
 * Handles duplicate names by appending short ID (first 8 chars) only when necessary
 * Format preference:
 * 1. appname (if no duplication)
 * 2. appname-xxxxxxxx (if name duplicates, where xxxxxxxx is first 8 chars of UUID without hyphens)
 * 3. appname-xxxxxxxx-2 (if both name and short ID duplicate)
 * 
 * @param appName - The application name
 * @param appId - The original application ID (for uniqueness)
 * @param existingSlugs - Optional set of existing slugs to avoid duplicates
 * @returns URL-friendly application slug
 */
export function generateApplicationSlug(
  appName: string, 
  appId?: string,
  existingSlugs?: Set<string>
): string {
  const baseSlug = toSlug(appName);
  
  // If no appId provided, use base slug with duplicate handling
  if (!appId) {
    // Fallback to generateUniqueSlug without ID
    return generateUniqueSlug(baseSlug, existingSlugs);
  }
  
  // Get short ID (first 8 characters of the UUID without hyphens)
  const shortId = appId.replace(/-/g, '').substring(0, 8);
  const slugWithShortId = `${baseSlug}-${shortId}`;
  
  // If no existing slugs to check, try base slug first (assume no duplication)
  if (!existingSlugs || existingSlugs.size === 0) {
    return baseSlug; // Return name-only slug when no duplication info available
  }
  
  // Strategy 1: Try base slug (appname only) if not duplicated
  if (!existingSlugs.has(baseSlug)) {
    return baseSlug;
  }
  
  // Strategy 2: Try slug with short ID if base slug is duplicated
  if (!existingSlugs.has(slugWithShortId)) {
    return slugWithShortId;
  }
  
  // Strategy 3: If both base slug and slug with short ID exist, add incremental numbers
  let counter = 2;
  let numberedSlug = `${baseSlug}-${shortId}-${counter}`;
  
  while (existingSlugs.has(numberedSlug)) {
    counter++;
    numberedSlug = `${baseSlug}-${shortId}-${counter}`;
  }
  
  return numberedSlug;
}

/**
 * Extract the original application ID from an application slug
 * Supports multiple slug formats:
 * 1. Full ID format: appname-32hexchars (legacy)
 * 2. Short ID format: appname-8hexchars (new default)
 * 3. Short ID with counter: appname-8hexchars-2
 * 
 * @param appSlug - The application slug to parse
 * @returns The extracted ID (full UUID, short ID, or null)
 */
export function extractAppIdFromSlug(appSlug: string): string | null {
  // Pattern 1: Full ID format (32 hex chars) - legacy
  const fullIdPattern = /-([0-9a-f]{32})$/;
  const fullMatch = appSlug.match(fullIdPattern);
  
  if (fullMatch) {
    const idWithoutHyphens = fullMatch[1];
    // Convert back to standard UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    if (idWithoutHyphens.length === 32) {
      return `${idWithoutHyphens.substring(0, 8)}-${idWithoutHyphens.substring(8, 12)}-${idWithoutHyphens.substring(12, 16)}-${idWithoutHyphens.substring(16, 20)}-${idWithoutHyphens.substring(20)}`;
    }
  }
  
  // Pattern 2: Short ID format (8 hex chars) - new default
  // Matches: appname-8hexchars OR appname-8hexchars-2 (counter)
  const shortIdPattern = /-([0-9a-f]{8})(?:-\d+)?$/;
  const shortMatch = appSlug.match(shortIdPattern);
  
  if (shortMatch) {
    // Return the 8-char short ID (without counter if present)
    return shortMatch[1]; // 8-character hex string
  }
  
  return null;
}

/**
 * Extract the original drawer ID from a drawer slug
 * Supports multiple slug formats:
 * 1. Full ID format: drawername-32hexchars (legacy)
 * 2. Short ID format: drawername-8hexchars (new default)
 * 3. Short ID with counter: drawername-8hexchars-2
 * 
 * @param drawerSlug - The drawer slug to parse
 * @returns The extracted ID (full UUID, short ID, or null)
 */
export function extractDrawerIdFromSlug(drawerSlug: string): string | null {
  // Pattern 1: Full ID format (32 hex chars) - legacy
  const fullIdPattern = /-([0-9a-f]{32})$/;
  const fullMatch = drawerSlug.match(fullIdPattern);
  
  if (fullMatch) {
    const idWithoutHyphens = fullMatch[1];
    // Convert back to standard UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    if (idWithoutHyphens.length === 32) {
      return `${idWithoutHyphens.substring(0, 8)}-${idWithoutHyphens.substring(8, 12)}-${idWithoutHyphens.substring(12, 16)}-${idWithoutHyphens.substring(16, 20)}-${idWithoutHyphens.substring(20)}`;
    }
  }
  
  // Pattern 2: Short ID format (8 hex chars) - new default
  // Matches: drawername-8hexchars OR drawername-8hexchars-2 (counter)
  const shortIdPattern = /-([0-9a-f]{8})(?:-\d+)?$/;
  const shortMatch = drawerSlug.match(shortIdPattern);
  
  if (shortMatch) {
    // Return the 8-char short ID (without counter if present)
    return shortMatch[1]; // 8-character hex string
  }
  
  return null;
}

/**
 * Extract the original ID from a slug (reverse operation)
 * 
 * @param slug - The slug to parse
 * @returns The original ID if embedded in slug, or null
 */
export function extractIdFromSlug(slug: string): string | null {
  // Check if slug ends with a UUID-like pattern
  const uuidPattern = /-[0-9a-f]{8}$/;
  const match = slug.match(uuidPattern);
  
  if (match) {
    return match[0].substring(1); // Remove the leading hyphen
  }
  
  return null;
}