import qrcode as qrcode
import qrcode.constants
from qrcode.image.styledpil import StyledPilImage

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)   #Esse erro, é por causa do logo, que pode estar atrapalhando, entao esse codigo pode ajudar arrumar esse erro  
qr.add_data('https://projetocantinajid-production.up.railway.app/')

imagem = qr.make_image(
    image_factory=StyledPilImage,    #Cria uma imagem do tipo PIL (Python Imaging Library, usa o PIL para fromar uma imagem
    embeded_image_path = r"C:\Users\nickk\Documents\VS Code\Projeto Cantina\static\imagens\LOGO-BRANCA-JID-3.png"  # Pega o caminho do logo, e coloca o logo no meio do qr code
)

imagem.save("qrcode_cantina1.png") # Sem o 1 é que tem problema, pois não teve o código do erro 

# import qrcode
# img = qrcode.make('https://projetocantinajid-production.up.railway.app')
# type(img)  # qrcode.image.pil.PilImage
# img.save("qrcode_cantina_sem_imagem.png")