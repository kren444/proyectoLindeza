-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 06-10-2025 a las 18:35:19
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `lindeza`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `administradores`
--

CREATE TABLE `administradores` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(150) NOT NULL,
  `password` varchar(255) NOT NULL,
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `administradores`
--

INSERT INTO `administradores` (`id`, `nombre`, `email`, `password`, `creado_en`) VALUES
(1, 'sara', 'sara@gmail.com', 'scrypt:32768:8:1$lj4QuhHCH9Md23aN$959014fa532086b65f4127723e8429f78f45370e16f5d7f48dff1532a627ab343cb56109bc8c6315c256fe342575b5b7ba894abdcab63c7c6acfebd95d88083e', '2025-09-04 14:30:08'),
(2, 'laura', 'laur@gmail.com', 'scrypt:32768:8:1$UwhpOqRuQIlh7azt$312850809412926ecd56c7573e7698ba2967c7f3c94940abe68c7cc8cf0709bcafd25a9504dfbcce79fa447a5e409642338c8a4e191b493ab43a01addc803e1a', '2025-09-04 15:45:18'),
(3, 'karen', 'karen@gmail.com', 'scrypt:32768:8:1$T0DyQcpkaxDjVTbC$ea69371509581b465a9e89cd2c0131bbdae2e456320a8678cf6405cad2c4471538b9e317d52b938918bc6e2abb982569b39e226799bba1ce2bbf4c5849242ac1', '2025-09-05 16:20:04'),
(4, 'jose', 'jose@gmail.com', 'scrypt:32768:8:1$juW9ABj87BhbPFOf$a2cfa0aadeb72da03dd4d943db0d751489b1c866e9fa90c4f840f74f439e9d90965c882aeeb9204c9678c2c0505b5696ed386b45a0afe917cc3ac1d838c10401', '2025-10-06 13:49:23');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `carrito`
--

CREATE TABLE `carrito` (
  `idcarrito` int(11) NOT NULL,
  `nombreproducto` varchar(100) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `direccion` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `carrito`
--

INSERT INTO `carrito` (`idcarrito`, `nombreproducto`, `nombre`, `direccion`, `email`) VALUES
(3, 'pantalon corto deportivo', 'jonier', 'calle 2', 'qwregtjgjk@gmail.com'),
(4, 'yiyos', 'xiomara', 'calle 9 carrera 5', 'xiomarauhsd@gmail.com'),
(5, 'yiyos', 'david', 'calle 9 carrera 5', 'qwregtjgjk@gmail.com');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `producto`
--

CREATE TABLE `producto` (
  `id` int(11) NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `descripcion` varchar(500) DEFAULT NULL,
  `precio` decimal(10,2) NOT NULL,
  `imagen` varchar(255) DEFAULT NULL,
  `categoria` varchar(80) DEFAULT NULL,
  `stock` int(11) NOT NULL DEFAULT 0,
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp(),
  `actualizado_en` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `producto`
--

INSERT INTO `producto` (`id`, `nombre`, `descripcion`, `precio`, `imagen`, `categoria`, `stock`, `creado_en`, `actualizado_en`) VALUES
(1, 'Base Media Cobertura', 'Base de cobertura media con un acabado natural', 28000.00, 'img/BASE MEDIA COBERTURA.jpg', 'Rostro', 40, '2025-09-02 12:53:05', '2025-10-06 14:43:56'),
(2, 'Base Queen', 'Base de alta cobertura ', 26000.00, 'img/BASE QUEEN.webp', 'Rostro', 30, '2025-09-02 12:53:05', '2025-09-02 12:53:05'),
(3, 'Base Trendy', 'Base de alta cobertura con duracion hasta de 12 horas aprueba de agua', 30000.00, 'img/BASE TRENDY.webp', 'Rostro', 50, '2025-09-02 12:53:05', '2025-09-02 12:53:05'),
(4, 'Base', 'Base de baja cobertura', 25000.00, 'img/BASE.jpg', 'Rostro', 35, '2025-09-02 12:53:05', '2025-09-02 12:53:05'),
(5, 'Base BB Cream MYK', 'Base dealta cobertura cremosa y suave con tu piel', 29000.00, 'img/BB CREAM.jpg', 'Rostro', 35, '2025-09-02 12:53:05', '2025-09-02 12:53:05'),
(6, 'Bronzer', 'Bronzer con acabado natural', 20000.00, 'img/BRONZER.jpg', 'Rostro', 25, '2025-09-02 12:53:05', '2025-09-02 12:53:05'),
(7, 'Contorno Trendy', 'Contorno de alta gama y calidad', 20000.00, 'img/CONTORNO TRENDY.webp', 'Rostro', 30, '2025-09-02 12:53:05', '2025-09-02 12:53:05');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `rol` enum('user','admin') DEFAULT 'user',
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT INTO `usuarios` (`id`, `nombre`, `email`, `password`, `rol`, `creado_en`) VALUES
(1, 'yolanda', 'yolanda@gmail.com', 'scrypt:32768:8:1$dTmm649ANqTQXRNC$04621e080b064c5d342b35b2a8e953b1d53a45cb38738336f6073e492b2bcaac2a6cb0dd2d51b6964f30d7eb112bf83e106305175df52969dbcf4d986502ff1e', 'user', '2025-09-04 14:29:37'),
(4, 'lopez', 'lopez@gmail.com', 'scrypt:32768:8:1$TdNvTTfyLYsiBFuG$aad9859c87328a28894cc2302ec14847f5eea8d06870c1a2b25d4bd657bfc1adadee4dbb1aca7cfaee56124ae2265f46d65aa6074cf0fffbc850bb1184bd05d4', 'user', '2025-09-05 12:43:03'),
(5, 'lalo', 'lalo@gmail.com', 'scrypt:32768:8:1$bBWHs9S4ZP2ey0dV$677e1d413e709a688213461c586386f1594a7fc649c4ba9953e2b8c9f05236289c575b9cc88708604ef7bd9b75e282ec3fcc5567c8ab4a4deaa7da07474f8f4c', 'user', '2025-09-05 13:56:54'),
(6, 'valery', 'valery@gmail.com', 'scrypt:32768:8:1$sq3B02MQ4CNFsi9K$85b7a399eff7145aa2750ad182088813836d8a2806bd921ca4ba3183101b7bc0d16867b635704c683f260bb6390a70e543b6277f4c82800769e04b65604dd3d5', 'user', '2025-09-05 16:19:30'),
(8, 'juan', 'juan@gmail.com', 'scrypt:32768:8:1$LEYKDW6DSrE6bkBO$7f2038aaa0ab8b4c47a449faf0ddb107627d63ea3332fa4cf85b670fd49bd65c6f9b2be1562fb9bde0db306831c55fe3b8f2dbfee731d00a543f5c489b74a6ff', 'user', '2025-10-06 13:41:00'),
(9, 'sofia', 'sofia@gmail.com', 'scrypt:32768:8:1$GP2BSWGiM8gncux6$e81f65da02a6980d61751519ca3ef6f80a5a02afe44f276b0c8324e6653f073786b79193ac2771193c65b5be42e728f2c56cf9f5b0e6ff0fbd6e89113d43fe53', 'user', '2025-10-06 13:42:26'),
(10, 'marin', 'marin@gmail.com', 'scrypt:32768:8:1$wIa8hLjhjuIrFGWA$b9f16e4ccf11ac41d575a7e037252536b067b5b67699979841171f3b844898b4a8d6a9133426fe508604ac8a4c3de07dc8479d4b9c17f353e76bdc6f8d1557f9', 'user', '2025-10-06 13:49:53');

--
-- Disparadores `usuarios`
--
DELIMITER $$
CREATE TRIGGER `solo_users` BEFORE INSERT ON `usuarios` FOR EACH ROW BEGIN
    IF NEW.rol <> 'user' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Solo se pueden insertar usuarios con rol = user en esta tabla';
    END IF;
END
$$
DELIMITER ;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `administradores`
--
ALTER TABLE `administradores`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indices de la tabla `carrito`
--
ALTER TABLE `carrito`
  ADD PRIMARY KEY (`idcarrito`);

--
-- Indices de la tabla `producto`
--
ALTER TABLE `producto`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `administradores`
--
ALTER TABLE `administradores`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `carrito`
--
ALTER TABLE `carrito`
  MODIFY `idcarrito` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de la tabla `producto`
--
ALTER TABLE `producto`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
