"""Extrae la caché de datos de las tablas dinámicas oficiales (sin Excel).

Python 3.10+; solo biblioteca estándar. --input-dir permite reproducir offline.
"""
import argparse
import csv
import hashlib
import io
import json
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from descargar_variables import download

BASE = 'http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/tablas_dinamicas/dowstream/individuales/'
FILES = ['TD_ventas_mercado_2010_2019.zip', 'TD_ventas_mercado.zip']
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
PRODUCTS = ['Gasoil Grado 1 (Agrogasoil)', 'Gasoil Grado 2 (Común)',
            'Gasoil Grado 3 (Ultra)', 'Nafta Grado 1 (Común)',
            'Nafta Grado 2 (Súper)', 'Nafta Grado 3 (Ultra)']


def extract(data):
    sums = defaultdict(lambda: defaultdict(Decimal))
    seen = set()
    negative_count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith('.xlsx')]
        if len(names) != 1:
            raise ValueError('Se esperaba exactamente un XLSX')
        with zipfile.ZipFile(io.BytesIO(archive.read(names[0]))) as book:
            definitions = [n for n in book.namelist() if n.startswith('xl/pivotCache/pivotCacheDefinition') and n.endswith('.xml')]
            if len(definitions) != 1:
                raise ValueError('Cambió la estructura de cachés de la tabla dinámica')
            definition = ET.fromstring(book.read(definitions[0]))
            fields = definition.find(NS + 'cacheFields')
            columns = [f.attrib['name'] for f in fields]
            required = {'anio', 'mes', 'producto', 'unidad', 'cantidad', 'tipodecomercializacion', 'subtipodecomercializacion', 'empresa', 'provincia'}
            if not required <= set(columns):
                raise ValueError(f'Esquema no reconocido: {columns}')
            items = [[c.attrib.get('v') for c in f.find(NS+'sharedItems')] if f.find(NS+'sharedItems') is not None else [] for f in fields]
            index = {name: i for i, name in enumerate(columns)}
            product_i = index['producto']
            selected = {i for i, p in enumerate(items[product_i]) if p.strip() in PRODUCTS}
            records = [n for n in book.namelist() if n.startswith('xl/pivotCache/pivotCacheRecords') and n.endswith('.xml')]
            if len(records) != 1:
                raise ValueError('Se esperaba una caché de registros')
            count = 0
            with book.open(records[0]) as source:
                context = ET.iterparse(source, events=('start', 'end'))
                _, root = next(context)
                for event, element in context:
                    if event != 'end' or element.tag != NS+'r':
                        continue
                    count += 1
                    children = list(element)
                    if len(children) != len(columns):
                        raise ValueError('Registro de caché incompleto')
                    cell = children[product_i]
                    relevant = int(cell.attrib['v']) in selected if cell.tag == NS+'x' else cell.attrib.get('v', '').strip() in PRODUCTS
                    if relevant:
                        values = [items[i][int(c.attrib['v'])] if c.tag == NS+'x' else c.attrib.get('v') for i, c in enumerate(children)]
                        row = dict(zip(columns, values))
                        if row['tipodecomercializacion'].strip() != 'Ventas':
                            raise ValueError('Tipo de comercialización inesperado')
                        if row['unidad'].strip() != '(m3)':
                            raise ValueError('Unidad inesperada')
                        # Bunker es abastecimiento de embarcaciones: excluir de ventas domésticas.
                        if row['subtipodecomercializacion'].strip().startswith('Bunker'):
                            element.clear(); root.clear(); continue
                        y, m = int(Decimal(row['anio'])), int(Decimal(row['mes']))
                        date = datetime(y, m, 1).strftime('%Y-%m-%d')
                        product = row['producto'].strip()
                        key = tuple(v for k, v in zip(columns, values) if k != 'cantidad')
                        if key in seen:
                            raise ValueError('Dimensiones duplicadas en la caché')
                        seen.add(key)
                        amount = Decimal(row['cantidad'])
                        if not amount.is_finite():
                            raise ValueError(f'Cantidad inválida: {amount}')
                        if amount < 0:
                            negative_count += 1  # Conservar ajustes negativos publicados.
                        sums[date][product] += amount
                    element.clear()
                    root.clear()
            if count != int(definition.attrib['recordCount']):
                raise ValueError('Cantidad de registros inconsistente')
    if not sums:
        raise ValueError('No hay datos de ventas seleccionados')
    return sums, count, negative_count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('data'))
    p.add_argument('--input-dir', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    combined, metadata = {}, []
    for filename in FILES:
        url = BASE + filename
        data = (a.input_dir / filename).read_bytes() if a.input_dir else download(url)
        sums, count, negative_count = extract(data)
        overlap = set(sums) & set(combined)
        if overlap:
            raise ValueError(f'Meses superpuestos entre fuentes: {sorted(overlap)}')
        combined.update(sums)
        (a.output / filename).write_bytes(data)
        metadata.append({'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'registros_cache': count, 'registros_negativos_conservados': negative_count, 'inicio': min(sums), 'fin': max(sums)})
    rows = []
    for date, values in sorted(combined.items()):
        if set(PRODUCTS) - set(values):
            raise ValueError(f'Categorías incompletas: {date}')
        rows.append([date, *[str(values[p]) for p in PRODUCTS], str(sum(values[p] for p in PRODUCTS[:3])), str(sum(values[p] for p in PRODUCTS[3:]))])
    dates = [r[0] for r in rows]
    missing = []
    y, m = int(dates[0][:4]), int(dates[0][5:7])
    while f'{y:04d}-{m:02d}-01' <= dates[-1]:
        d = f'{y:04d}-{m:02d}-01'
        if d not in combined:
            missing.append(d)
        y, m = (y+1, 1) if m == 12 else (y, m+1)
    columns = ['fecha', 'gasoil_grado1_m3', 'gasoil_grado2_m3', 'gasoil_grado3_m3', 'nafta_grado1_m3', 'nafta_grado2_m3', 'nafta_grado3_m3', 'ventas_gasoil_grados1a3_m3', 'ventas_nafta_grados1a3_m3']
    with (a.output / 'combustibles_mensual.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f); writer.writerow(columns); writer.writerows(rows)
    report = {'fuentes': metadata, 'procesado_utc': datetime.now(timezone.utc).isoformat(), 'modo': 'archivo_local' if a.input_dir else 'descarga', 'frecuencia': 'mensual', 'inicio': dates[0], 'fin': dates[-1], 'filas': len(rows), 'meses_faltantes': missing, 'alcance': 'Ventas excluyendo empresas del sector y bunker; grados 1 a 3; todas las provincias y sectores domésticos', 'advertencia': 'Descarga HTTP oficial; la estructura de la caché puede cambiar. No equivale directamente al volumen sujeto a corte.'}
    (a.output / 'combustibles_metadata.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
