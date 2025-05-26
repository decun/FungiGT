const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
    username: {
        type: String,
        required: [true, 'Username es requerido'],
        unique: true,
        trim: true,
        minlength: [3, 'Username debe tener al menos 3 caracteres'],
        maxlength: [30, 'Username no puede exceder 30 caracteres']
    },
    email: {
        type: String,
        required: [true, 'Email es requerido'],
        unique: true,
        trim: true,
        lowercase: true,
        match: [/^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,3})+$/, 'Email inválido']
    },
    password: {
        type: String,
        required: [true, 'Password es requerido'],
        minlength: [6, 'Password debe tener al menos 6 caracteres']
    },
    firstName: {
        type: String,
        required: [true, 'Nombre es requerido'],
        trim: true,
        maxlength: [50, 'Nombre no puede exceder 50 caracteres']
    },
    lastName: {
        type: String,
        required: [true, 'Apellido es requerido'],
        trim: true,
        maxlength: [50, 'Apellido no puede exceder 50 caracteres']
    },
    role: {
        type: String,
        enum: ['admin', 'researcher', 'viewer'],
        default: 'researcher'
    },
    isActive: {
        type: Boolean,
        default: true
    },
    lastLogin: {
        type: Date
    },
    profileImage: {
        type: String,
        default: null
    }
}, {
    timestamps: true
});

// Hash password antes de guardar
userSchema.pre('save', async function(next) {
    if (!this.isModified('password')) return next();
    
    try {
        const salt = await bcrypt.genSalt(12);
        this.password = await bcrypt.hash(this.password, salt);
        next();
    } catch (error) {
        next(error);
    }
});

// Método para comparar contraseñas
userSchema.methods.comparePassword = async function(candidatePassword) {
    return bcrypt.compare(candidatePassword, this.password);
};

// Método para obtener datos públicos del usuario
userSchema.methods.toPublicJSON = function() {
    return {
        id: this._id,
        username: this.username,
        email: this.email,
        firstName: this.firstName,
        lastName: this.lastName,
        fullName: `${this.firstName} ${this.lastName}`,
        role: this.role,
        isActive: this.isActive,
        lastLogin: this.lastLogin,
        profileImage: this.profileImage,
        createdAt: this.createdAt
    };
};

module.exports = mongoose.model('User', userSchema); 