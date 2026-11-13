// Usado solo por la build de despliegue en Render (`ng build --configuration=render`).
// Si el nombre del servicio backend en Render cambia (p. ej. porque
// "seguimiento-ti-backend" ya estaba tomado y Render le puso un sufijo),
// actualizar esta URL para que coincida.
export const environment = {
  production: true,
  apiBaseUrl: 'https://seguimiento-ti-backend.onrender.com/api/v1',
};
