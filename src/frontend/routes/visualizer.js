const express = require('express');
const router = express.Router();

function ensureAuthenticated(req, res, next) {
  if (req.session.userId) {
    return next();
  }
  res.redirect('/auth/login');
}

router.get('/', (req, res) => {
  res.render('visualizer');
});
//router.get('/', ensureAuthenticated, (req, res) => {
//  res.render('annotator');
//});

module.exports = router;
