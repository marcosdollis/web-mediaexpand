from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Permissão para o dono (OWNER) - acesso total"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_owner()


class IsFranchiseeOrOwner(permissions.BasePermission):
    """Permissão para franqueados ou dono"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_franchisee() or request.user.is_owner()
        )


class IsClientOrAbove(permissions.BasePermission):
    """Permissão para cliente, franqueado ou dono"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsOwnerOfObject(permissions.BasePermission):
    """Verifica se o usuário é dono do objeto ou tem permissões superiores"""
    
    def has_object_permission(self, request, view, obj):
        # Dono tem acesso total
        if request.user.is_owner():
            return True
        
        # Franqueado pode acessar seus próprios objetos
        if request.user.is_franchisee():
            if hasattr(obj, 'franqueado'):
                return obj.franqueado == request.user
            if hasattr(obj, 'municipio'):
                return obj.municipio.franqueado == request.user
        
        # Cliente pode acessar apenas seus próprios objetos
        if request.user.is_client():
            if hasattr(obj, 'cliente'):
                return obj.cliente.user == request.user
            if hasattr(obj, 'user'):
                return obj.user == request.user
        
        return False


class CanManageClients(permissions.BasePermission):
    """Permissão para gerenciar clientes (apenas franqueado e dono)"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_franchisee() or request.user.is_owner()
        )


class CanManagePlaylists(permissions.BasePermission):
    """Permissão para gerenciar playlists (apenas franqueado e dono)"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_franchisee() or request.user.is_owner()
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_owner():
            return True
        if request.user.is_franchisee():
            return obj.franqueado == request.user
        return False


class CanManageVideos(permissions.BasePermission):
    """Permissão para gerenciar vídeos"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Dono vê tudo
        if request.user.is_owner():
            return True
        
        # Franqueado vê vídeos de seus clientes
        if request.user.is_franchisee():
            return obj.cliente.franqueado == request.user
        
        # Cliente vê apenas seus próprios vídeos
        if request.user.is_client():
            return obj.cliente.user == request.user
        
        return False
