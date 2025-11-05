from django.shortcuts import render

# Create your views here.
def panel_view(request):
  
  return render(request,'Moldeo/panel_principal.html')

def Registrar_Orden_view(request):
  
  return render(request,'Moldeo/Registrar_orden.html')