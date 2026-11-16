import { ActivatedRoute, Params, Router } from '@angular/router';

/** Refleja filtros en la URL solo si cambian. Navegar a los mismos parámetros
 * desde el constructor de una pantalla cancela la navegación en curso
 * ("superada por otra"), y sin `NavigationEnd` el menú y las migas no se
 * actualizan. */
export function sincronizarQueryParams(router: Router, ruta: ActivatedRoute, queryParams: Params): void {
  const actuales = ruta.snapshot.queryParams;
  const claves = new Set([...Object.keys(actuales), ...Object.keys(queryParams)]);
  const iguales = [...claves].every((clave) => {
    const nuevo = queryParams[clave];
    const nuevoTexto = nuevo === null || nuevo === undefined ? '' : String(nuevo);
    return String(actuales[clave] ?? '') === nuevoTexto;
  });
  if (!iguales) {
    void router.navigate([], { relativeTo: ruta, queryParams });
  }
}
