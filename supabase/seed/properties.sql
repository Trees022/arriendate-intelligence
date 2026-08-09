with seed as (
  select *
  from jsonb_to_recordset($seed$
  [
    {"id":"10000000-0000-4000-8000-000000000001","title":"Departamento Los Castaños","description":"Departamento luminoso en un entorno residencial, con segundo dormitorio apto para escritorio.","operation_type":"rent","property_type":"apartment","city":"Viña del Mar","sector":"Los Castaños","monthly_price":670000,"sale_price":null,"bedrooms":2,"bathrooms":2,"parking_spaces":1,"pet_policy":"allowed","furnished":false,"square_meters":68,"amenities":["balcón","conserjería","bodega"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000002","title":"Estudio Poniente","description":"Estudio amoblado de distribución compacta y conexión rápida con el centro de Viña.","operation_type":"rent","property_type":"studio","city":"Viña del Mar","sector":"Poniente","monthly_price":480000,"sale_price":null,"bedrooms":1,"bathrooms":1,"parking_spaces":0,"pet_policy":"not_allowed","furnished":true,"square_meters":34,"amenities":["conserjería","lavandería"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000003","title":"Vista Jardín del Mar","description":"Departamento amplio con terraza y espacios comunes, ubicado en un sector de carácter residencial.","operation_type":"rent","property_type":"apartment","city":"Viña del Mar","sector":"Jardín del Mar","monthly_price":850000,"sale_price":null,"bedrooms":3,"bathrooms":2,"parking_spaces":2,"pet_policy":"unknown","furnished":false,"square_meters":92,"amenities":["terraza","piscina","bodega"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000004","title":"Departamento Recreo Alto","description":"Unidad de dos dormitorios en calle interior; la descripción del propietario destaca poco flujo vehicular.","operation_type":"rent","property_type":"apartment","city":"Viña del Mar","sector":"Recreo","monthly_price":620000,"sale_price":null,"bedrooms":2,"bathrooms":1,"parking_spaces":1,"pet_policy":"allowed","furnished":false,"square_meters":61,"amenities":["balcón","áreas verdes"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000005","title":"Departamento Centro Viña","description":"Departamento renovado próximo al centro, con cocina equipada y locomoción cercana.","operation_type":"rent","property_type":"apartment","city":"Viña del Mar","sector":"Centro","monthly_price":590000,"sale_price":null,"bedrooms":2,"bathrooms":1,"parking_spaces":null,"pet_policy":"allowed","furnished":true,"square_meters":57,"amenities":["ascensor","cocina equipada"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000006","title":"Casa Familiar Miraflores","description":"Casa independiente con patio, cuatro dormitorios y espacios diferenciados para trabajo o estudio.","operation_type":"buy","property_type":"house","city":"Viña del Mar","sector":"Miraflores","monthly_price":null,"sale_price":285000000,"bedrooms":4,"bathrooms":3,"parking_spaces":2,"pet_policy":"allowed","furnished":false,"square_meters":168,"amenities":["patio","bodega","quincho"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000007","title":"Loft Cerro Alegre","description":"Loft amoblado en edificio restaurado, con espacio integrado y vista parcial a la bahía.","operation_type":"rent","property_type":"loft","city":"Valparaíso","sector":"Cerro Alegre","monthly_price":720000,"sale_price":null,"bedrooms":2,"bathrooms":2,"parking_spaces":0,"pet_policy":"allowed","furnished":true,"square_meters":76,"amenities":["terraza común","bicicletero"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000008","title":"Departamento Playa Ancha","description":"Departamento de tres dormitorios cercano a servicios universitarios y plazas del sector.","operation_type":"rent","property_type":"apartment","city":"Valparaíso","sector":"Playa Ancha","monthly_price":520000,"sale_price":null,"bedrooms":3,"bathrooms":1,"parking_spaces":1,"pet_policy":"allowed","furnished":false,"square_meters":72,"amenities":["bodega","área de juegos"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000009","title":"Departamento Barón Compacto","description":"Unidad de un dormitorio con acceso cercano a transporte público y comercio de barrio.","operation_type":"rent","property_type":"apartment","city":"Valparaíso","sector":"Barón","monthly_price":450000,"sale_price":null,"bedrooms":1,"bathrooms":1,"parking_spaces":0,"pet_policy":"not_allowed","furnished":false,"square_meters":42,"amenities":["conserjería","gimnasio"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000010","title":"Departamento Parque Curauma","description":"Departamento familiar frente a áreas verdes, con tercer dormitorio utilizable como oficina.","operation_type":"rent","property_type":"apartment","city":"Valparaíso","sector":"Curauma","monthly_price":680000,"sale_price":null,"bedrooms":3,"bathrooms":2,"parking_spaces":1,"pet_policy":"allowed","furnished":false,"square_meters":84,"amenities":["áreas verdes","piscina","bodega"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000011","title":"Bosques de Montemar","description":"Departamento de tres dormitorios con terraza amplia y distribución separada de áreas comunes.","operation_type":"rent","property_type":"apartment","city":"Concón","sector":"Bosques de Montemar","monthly_price":980000,"sale_price":null,"bedrooms":3,"bathrooms":2,"parking_spaces":2,"pet_policy":"allowed","furnished":false,"square_meters":104,"amenities":["terraza","piscina","gimnasio","bodega"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000012","title":"Departamento Concón Centro","description":"Departamento funcional próximo a comercio local, con dos dormitorios y estacionamiento.","operation_type":"rent","property_type":"apartment","city":"Concón","sector":"Centro","monthly_price":610000,"sale_price":null,"bedrooms":2,"bathrooms":2,"parking_spaces":1,"pet_policy":"unknown","furnished":false,"square_meters":64,"amenities":["ascensor","conserjería"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000013","title":"Costa de Montemar Amoblado","description":"Departamento amoblado con balcón y espacio de comedor separado del estar.","operation_type":"rent","property_type":"apartment","city":"Concón","sector":"Costa de Montemar","monthly_price":780000,"sale_price":null,"bedrooms":2,"bathrooms":2,"parking_spaces":1,"pet_policy":"not_allowed","furnished":true,"square_meters":73,"amenities":["balcón","piscina","gimnasio"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000014","title":"Casa Higuerillas","description":"Casa de dos niveles con patio protegido, cuatro dormitorios y sala independiente.","operation_type":"buy","property_type":"house","city":"Concón","sector":"Higuerillas","monthly_price":null,"sale_price":420000000,"bedrooms":4,"bathrooms":3,"parking_spaces":2,"pet_policy":"allowed","furnished":false,"square_meters":190,"amenities":["patio","sala multiuso","bodega"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000015","title":"Departamento El Belloto","description":"Departamento de dos dormitorios en condominio con áreas verdes y acceso controlado.","operation_type":"rent","property_type":"apartment","city":"Quilpué","sector":"El Belloto","monthly_price":470000,"sale_price":null,"bedrooms":2,"bathrooms":1,"parking_spaces":1,"pet_policy":"allowed","furnished":false,"square_meters":58,"amenities":["áreas verdes","juegos infantiles"],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000016","title":"Departamento Marga Marga","description":"Unidad de tres dormitorios con buena distribución interior y terraza cerrada.","operation_type":"rent","property_type":"apartment","city":"Quilpué","sector":"Marga Marga","monthly_price":560000,"sale_price":null,"bedrooms":3,"bathrooms":2,"parking_spaces":1,"pet_policy":"unknown","furnished":false,"square_meters":79,"amenities":["terraza","conserjería"],"availability_status":"reserved"},
    {"id":"10000000-0000-4000-8000-000000000017","title":"Departamento Valencia","description":"Registro sintético incompleto de una unidad económica; dormitorios y estacionamiento por confirmar.","operation_type":"rent","property_type":"apartment","city":"Quilpué","sector":"Valencia","monthly_price":430000,"sale_price":null,"bedrooms":null,"bathrooms":1,"parking_spaces":null,"pet_policy":"allowed","furnished":null,"square_meters":null,"amenities":[],"availability_status":"available"},
    {"id":"10000000-0000-4000-8000-000000000018","title":"Casa Los Pinos","description":"Casa pareada con patio posterior, tres dormitorios y estacionamiento para dos vehículos.","operation_type":"buy","property_type":"house","city":"Quilpué","sector":"Los Pinos","monthly_price":null,"sale_price":135000000,"bedrooms":3,"bathrooms":2,"parking_spaces":2,"pet_policy":"allowed","furnished":false,"square_meters":112,"amenities":["patio","logia","bodega"],"availability_status":"available"}
  ]
  $seed$::jsonb) as item(
    id uuid,
    title text,
    description text,
    operation_type text,
    property_type text,
    city text,
    sector text,
    monthly_price bigint,
    sale_price bigint,
    bedrooms smallint,
    bathrooms smallint,
    parking_spaces smallint,
    pet_policy text,
    furnished boolean,
    square_meters numeric,
    amenities jsonb,
    availability_status text
  )
)
insert into public.properties (
  id, title, description, operation_type, property_type, city, sector,
  monthly_price, sale_price, currency, bedrooms, bathrooms, parking_spaces,
  pet_policy, furnished, square_meters, amenities, availability_status,
  source_text, embedding_text
)
select
  seed.id,
  seed.title,
  seed.description,
  seed.operation_type,
  seed.property_type,
  seed.city,
  seed.sector,
  seed.monthly_price,
  seed.sale_price,
  'CLP',
  seed.bedrooms,
  seed.bathrooms,
  seed.parking_spaces,
  seed.pet_policy,
  seed.furnished,
  seed.square_meters,
  array(select jsonb_array_elements_text(seed.amenities)),
  seed.availability_status,
  seed.description,
  concat_ws('. ', seed.title, seed.description, 'Ciudad: ' || seed.city, 'Sector: ' || seed.sector)
from seed
on conflict (id) do update set
  title = excluded.title,
  description = excluded.description,
  updated_at = now();
