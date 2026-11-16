// Usado solo por la build de QA en Render (`ng build --configuration=qa`).
// Debe coincidir con el servicio `seguimiento-ti-qa-backend` de render.yaml.
export const environment = {
  production: true,
  apiBaseUrl: 'https://seguimiento-ti-qa-backend.onrender.com/api/v1',
};
