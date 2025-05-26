// config/database.js

// Comentamos o eliminamos la lógica de conexión a MongoDB
// const mongoose = require('mongoose');

// mongoose.connect('mongodb://localhost/fungitg', {
//   useNewUrlParser: true,
//   useUnifiedTopology: true,
// });

// const db = mongoose.connection;
// db.on('error', console.error.bind(console, 'MongoDB connection error:'));
// db.once('open', () => {
//   console.log('Connected to MongoDB');
// });

// En su lugar, exportamos un objeto falso para simular la conexión
module.exports = {
  connection: {
    on: () => {},
    once: () => {},
  },
  model: (modelName, schema) => {
    return {
      find: () => Promise.resolve([]),
      findOne: () => Promise.resolve(null),
      create: (data) => Promise.resolve(data),
      // Agrega más métodos según sea necesario
    };
  },
};

console.log('MongoDB connection disabled');
