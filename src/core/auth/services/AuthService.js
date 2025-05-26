const jwt = require('jsonwebtoken');
const User = require('../models/User');

class AuthService {
    constructor() {
        this.jwtSecret = process.env.JWT_SECRET || 'fungi-gt-secret-key-2024-super-secure';
        this.jwtExpiration = process.env.JWT_EXPIRATION || '24h';
        this.refreshTokenExpiration = process.env.REFRESH_TOKEN_EXPIRATION || '7d';
    }

    // Generar JWT token
    generateToken(user) {
        const payload = {
            id: user._id,
            username: user.username,
            email: user.email,
            role: user.role
        };

        return jwt.sign(payload, this.jwtSecret, {
            expiresIn: this.jwtExpiration
        });
    }

    // Generar refresh token
    generateRefreshToken(user) {
        const payload = {
            id: user._id,
            type: 'refresh'
        };

        return jwt.sign(payload, this.jwtSecret, {
            expiresIn: this.refreshTokenExpiration
        });
    }

    // Verificar JWT token
    verifyToken(token) {
        try {
            return jwt.verify(token, this.jwtSecret);
        } catch (error) {
            throw new Error('Token inválido o expirado');
        }
    }

    // Registrar nuevo usuario
    async register(userData) {
        try {
            // Verificar si el usuario ya existe
            const existingUser = await User.findOne({
                $or: [
                    { email: userData.email.toLowerCase() },
                    { username: userData.username }
                ]
            });

            if (existingUser) {
                if (existingUser.email === userData.email.toLowerCase()) {
                    throw new Error('El email ya está registrado');
                }
                if (existingUser.username === userData.username) {
                    throw new Error('El username ya está en uso');
                }
            }

            // Crear nuevo usuario
            const user = new User({
                ...userData,
                email: userData.email.toLowerCase()
            });
            
            await user.save();

            // Generar tokens
            const token = this.generateToken(user);
            const refreshToken = this.generateRefreshToken(user);

            return {
                user: user.toPublicJSON(),
                token,
                refreshToken
            };
        } catch (error) {
            throw error;
        }
    }

    // Iniciar sesión
    async login(email, password) {
        try {
            // Buscar usuario por email
            const user = await User.findOne({ 
                email: email.toLowerCase() 
            });
            
            if (!user) {
                throw new Error('Credenciales inválidas');
            }

            if (!user.isActive) {
                throw new Error('Cuenta desactivada. Contacta al administrador');
            }

            // Verificar contraseña
            const isPasswordValid = await user.comparePassword(password);
            
            if (!isPasswordValid) {
                throw new Error('Credenciales inválidas');
            }

            // Actualizar último login
            user.lastLogin = new Date();
            await user.save();

            // Generar tokens
            const token = this.generateToken(user);
            const refreshToken = this.generateRefreshToken(user);

            return {
                user: user.toPublicJSON(),
                token,
                refreshToken
            };
        } catch (error) {
            throw error;
        }
    }

    // Obtener usuario por ID
    async getUserById(userId) {
        try {
            const user = await User.findById(userId);
            if (!user) {
                throw new Error('Usuario no encontrado');
            }
            return user.toPublicJSON();
        } catch (error) {
            throw error;
        }
    }

    // Cambiar contraseña
    async changePassword(userId, currentPassword, newPassword) {
        try {
            const user = await User.findById(userId);
            if (!user) {
                throw new Error('Usuario no encontrado');
            }

            const isCurrentPasswordValid = await user.comparePassword(currentPassword);
            if (!isCurrentPasswordValid) {
                throw new Error('Contraseña actual incorrecta');
            }

            user.password = newPassword;
            await user.save();

            return { message: 'Contraseña actualizada exitosamente' };
        } catch (error) {
            throw error;
        }
    }

    // Actualizar perfil
    async updateProfile(userId, updateData) {
        try {
            const allowedUpdates = ['firstName', 'lastName', 'username', 'profileImage'];
            const updates = {};
            
            Object.keys(updateData).forEach(key => {
                if (allowedUpdates.includes(key)) {
                    updates[key] = updateData[key];
                }
            });

            const user = await User.findByIdAndUpdate(
                userId, 
                updates, 
                { new: true, runValidators: true }
            );

            if (!user) {
                throw new Error('Usuario no encontrado');
            }

            return user.toPublicJSON();
        } catch (error) {
            throw error;
        }
    }

    // Listar usuarios (solo admin)
    async getAllUsers(page = 1, limit = 10, search = '') {
        try {
            const skip = (page - 1) * limit;
            
            let query = {};
            if (search) {
                query = {
                    $or: [
                        { username: { $regex: search, $options: 'i' } },
                        { email: { $regex: search, $options: 'i' } },
                        { firstName: { $regex: search, $options: 'i' } },
                        { lastName: { $regex: search, $options: 'i' } }
                    ]
                };
            }

            const users = await User.find(query)
                .select('-password')
                .sort({ createdAt: -1 })
                .skip(skip)
                .limit(limit);

            const total = await User.countDocuments(query);

            return {
                users: users.map(user => user.toPublicJSON()),
                pagination: {
                    page,
                    limit,
                    total,
                    pages: Math.ceil(total / limit)
                }
            };
        } catch (error) {
            throw error;
        }
    }

    // Actualizar rol de usuario (solo admin)
    async updateUserRole(userId, newRole) {
        try {
            if (!['admin', 'researcher', 'viewer'].includes(newRole)) {
                throw new Error('Rol no válido');
            }

            const user = await User.findByIdAndUpdate(
                userId,
                { role: newRole },
                { new: true, runValidators: true }
            );

            if (!user) {
                throw new Error('Usuario no encontrado');
            }

            return user.toPublicJSON();
        } catch (error) {
            throw error;
        }
    }

    // Activar/desactivar usuario (solo admin)
    async toggleUserActive(userId, isActive) {
        try {
            const user = await User.findByIdAndUpdate(
                userId,
                { isActive },
                { new: true, runValidators: true }
            );

            if (!user) {
                throw new Error('Usuario no encontrado');
            }

            return user.toPublicJSON();
        } catch (error) {
            throw error;
        }
    }

    // Renovar token de acceso con refresh token
    async refreshAccessToken(refreshToken) {
        try {
            // Verificar el refresh token
            const decoded = this.verifyToken(refreshToken);
            
            // Verificar que sea un refresh token
            if (!decoded.type || decoded.type !== 'refresh') {
                throw new Error('Token inválido');
            }
            
            // Obtener el usuario
            const user = await User.findById(decoded.id);
            if (!user) {
                throw new Error('Usuario no encontrado');
            }
            
            if (!user.isActive) {
                throw new Error('Cuenta desactivada. Contacta al administrador');
            }
            
            // Generar nuevo token de acceso
            const token = this.generateToken(user);
            
            return {
                token,
                user: user.toPublicJSON()
            };
        } catch (error) {
            throw error;
        }
    }

    // Crear usuario admin (solo para inicialización)
    async createAdminUser(adminData) {
        try {
            const existingAdmin = await User.findOne({ role: 'admin' });
            
            if (existingAdmin) {
                return { message: 'Ya existe un administrador en el sistema' };
            }

            const admin = new User({
                ...adminData,
                role: 'admin',
                isActive: true
            });
            
            await admin.save();
            
            return {
                message: 'Administrador creado exitosamente',
                admin: admin.toPublicJSON()
            };
        } catch (error) {
            throw error;
        }
    }
}

module.exports = new AuthService(); 