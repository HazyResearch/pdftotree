echo "Downloading pretrained vision model..."
url=http://i.stanford.edu/hazy/share/fonduer/visualtable/paleo_visual_model.h5
data_file=paleo_visual_model.h5
if type curl &>/dev/null; then
    curl -RLO $url
elif type wget &>/dev/null; then
    wget -N -nc $url
fi 
echo "Done!"
