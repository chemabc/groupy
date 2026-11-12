-- Prepara la base de datos de la bóveda de identidad, separada de la de la plataforma.
-- PostgreSQL ejecuta este fichero UNA sola vez, al crear el volumen de datos (instalación nueva).
-- En una instalación que ya existía, hay que ejecutarlo a mano (ver docs/boveda-de-identidad.md).
-- Las contraseñas de aquí solo valen para desarrollo; en producción se cambian.

-- Crea el usuario propio de la bóveda.
--     LOGIN: puede iniciar sesión
--     PASSWORD 'boveda': su contraseña (solo desarrollo)
--     CREATEDB: puede crear bases de datos; lo necesita Django para la base de pruebas «test_boveda»
CREATE ROLE boveda LOGIN PASSWORD 'boveda' CREATEDB;

-- Crea la base de datos de la bóveda.
--     OWNER boveda: su dueño es el usuario de la bóveda, no el de la plataforma
CREATE DATABASE boveda OWNER boveda;

-- Quita a cualquier otro usuario el permiso de conectarse a la bóveda.
--     PUBLIC: «todos los usuarios»; el dueño (boveda) sigue pudiendo conectarse
REVOKE CONNECT ON DATABASE boveda FROM PUBLIC;
