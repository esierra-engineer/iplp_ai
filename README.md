# iplp_ai

Repositorio de datos y herramientas para casos del modelo PLP (Planificación de Largo Plazo) del sistema eléctrico chileno.

## Contenido del repositorio

- `xlsm/IPLP20251001_c00.xlsm`: libro Excel de entrada del caso.
- `xla/MacroPLP_I_20250508.xla`: add-in con macros VBA que generan archivos `.dat`.
- `xla/FUNCCDEC_CDEC.xla`: add-in de funciones de apoyo para cálculos CDEC.
- `dat/static`: archivos `.dat` de configuración estática.
- `dat/block_dependant`: archivos `.dat` dependientes de etapa/bloque.
- `portal/`: implementación Python/FastAPI para importar casos y generar archivos `.dat` sin depender del flujo Excel/VBA tradicional.

## Flujo de trabajo típico (Excel/VBA)

1. Abrir `xlsm/IPLP20251001_c00.xlsm` en Excel con los add-ins de `xla/` cargados.
2. Editar los datos de entrada en las hojas correspondientes.
3. Ejecutar las macros `Archivo_*` para regenerar los archivos en `dat/`.

## Portal Python

El subproyecto `portal/` tiene su propia documentación en `portal/README.md`, incluyendo:

- instalación de dependencias,
- importación de casos desde `.xlsm`,
- ejecución de la aplicación web,
- y pruebas.
