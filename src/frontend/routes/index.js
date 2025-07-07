const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.render('landing');
});

// Ruta para el perfil de usuario
router.get('/profile', (req, res) => {
  res.render('profile', {
    title: 'Perfil de Usuario | FungiGT',
    user: req.user || {}
  });
});

// Ruta para el historial de uso
router.get('/history', (req, res) => {
  res.render('history', {
    title: 'Historial de Uso | FungiGT',
    user: req.user || {}
  });
});

// Ruta para la configuración
router.get('/config', (req, res) => {
  res.render('config', {
    title: 'Configuración | FungiGT',
    user: req.user || {}
  });
});

module.exports = router;
