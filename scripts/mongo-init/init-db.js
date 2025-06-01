// Script de inicialización de MongoDB para FungiGT
print("🚀 Inicializando base de datos FungiGT...");

// Cambiar a la base de datos fungigt
db = db.getSiblingDB('fungigt');

// Crear usuario para la aplicación
db.createUser({
  user: 'fungigt_user',
  pwd: 'fungigt_password_2024',
  roles: [
    {
      role: 'readWrite',
      db: 'fungigt'
    }
  ]
});

// Crear colecciones iniciales
db.createCollection('users');
db.createCollection('genomes');
db.createCollection('analyses');
db.createCollection('annotations');
db.createCollection('quality_reports');

// Insertar usuario admin por defecto
db.users.insertOne({
  _id: ObjectId(),
  username: 'admin',
  email: 'admin@fungigt.com',
  firstName: 'Administrator',
  lastName: 'FungiGT',
  password: '$2b$10$rH8Q6yKzGjq8yR3mF4N0XOKvZ8L1mW2nE5pA7sT9dC3hG6jK2lM8S', // password: admin123
  role: 'admin',
  isEmailVerified: true,
  createdAt: new Date(),
  updatedAt: new Date()
});

// Crear índices para optimizar consultas
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ username: 1 }, { unique: true });
db.genomes.createIndex({ accession: 1 });
db.genomes.createIndex({ organism: 1 });
db.analyses.createIndex({ genomeId: 1 });
db.analyses.createIndex({ status: 1 });

print("✅ Base de datos FungiGT inicializada correctamente");
print("📊 Usuario admin creado - email: admin@fungigt.com, password: admin123"); 