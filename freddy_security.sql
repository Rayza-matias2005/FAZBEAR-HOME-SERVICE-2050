CREATE DATABASE IF NOT EXISTS freddy_security
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE freddy_security;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT NOT NULL AUTO_INCREMENT,
    usuario VARCHAR(100) NOT NULL,
    salt CHAR(32) NOT NULL,
    senha CHAR(64) NOT NULL,
    criado_em DATETIME NOT NULL,
    recovery_salt CHAR(32) NULL,
    recovery_hash CHAR(64) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_usuario (usuario)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'freddy_app'@'%' IDENTIFIED BY 'Freddy_SQL_2026!';
GRANT SELECT, INSERT, UPDATE ON freddy_security.usuarios TO 'freddy_app'@'%';
FLUSH PRIVILEGES;
