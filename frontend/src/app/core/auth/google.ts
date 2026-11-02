/** PKCE para el login con Google (Authorization Code + PKCE, api-contrato.md §2).
 * El `code_verifier` se genera y se guarda aquí, en el frontend; el backend
 * nunca lo ve hasta el canje final en /auth/google/callback/.
 */

const ALFABETO_VERIFICADOR =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';

const CLAVE_CODE_VERIFIER = 'sp_google_code_verifier';
const CLAVE_STATE = 'sp_google_state';
const CLAVE_RETURN_URL = 'sp_google_return_url';

function base64UrlDesdeBuffer(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binario = '';
  for (const byte of bytes) {
    binario += String.fromCharCode(byte);
  }
  return btoa(binario).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** Cadena aleatoria de 64 caracteres (dentro del rango 43–128 que exige PKCE). */
export function generarCodeVerifier(): string {
  const valores = crypto.getRandomValues(new Uint8Array(64));
  return Array.from(valores, (valor) => ALFABETO_VERIFICADOR[valor % ALFABETO_VERIFICADOR.length]).join(
    '',
  );
}

export async function calcularCodeChallenge(codeVerifier: string): Promise<string> {
  const datos = new TextEncoder().encode(codeVerifier);
  const hash = await crypto.subtle.digest('SHA-256', datos);
  return base64UrlDesdeBuffer(hash);
}

export function guardarIntentoGoogle(codeVerifier: string, state: string, returnUrl: string): void {
  sessionStorage.setItem(CLAVE_CODE_VERIFIER, codeVerifier);
  sessionStorage.setItem(CLAVE_STATE, state);
  sessionStorage.setItem(CLAVE_RETURN_URL, returnUrl);
}

export interface IntentoGoogleGuardado {
  codeVerifier: string | null;
  state: string | null;
  returnUrl: string | null;
}

export function leerIntentoGoogle(): IntentoGoogleGuardado {
  return {
    codeVerifier: sessionStorage.getItem(CLAVE_CODE_VERIFIER),
    state: sessionStorage.getItem(CLAVE_STATE),
    returnUrl: sessionStorage.getItem(CLAVE_RETURN_URL),
  };
}

export function limpiarIntentoGoogle(): void {
  sessionStorage.removeItem(CLAVE_CODE_VERIFIER);
  sessionStorage.removeItem(CLAVE_STATE);
  sessionStorage.removeItem(CLAVE_RETURN_URL);
}
